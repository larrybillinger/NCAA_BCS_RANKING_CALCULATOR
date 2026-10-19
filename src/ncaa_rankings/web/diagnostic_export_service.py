from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from .display_scores import display_scores_for_prediction
from .models import Game, Team
from .prediction_service import (
    FALLBACK_POINTS_PER_RANK,
    MAX_POINTS_PER_RANK,
    MAX_PROJECTED_MARGIN,
    MIN_POINTS_PER_RANK,
    fit_calibration,
)
from .ranking_service import get_snapshot
from .research_prediction_service import (
    DEFAULT_PRIOR_GAMES,
    OFFDEF_MARGIN_WEIGHT,
    RANK_MARGIN_WEIGHT,
    fit_scoring_profiles,
)
from .stats_service import (
    AccuracyMetrics,
    metrics_for_rows,
    official_prediction_rows,
    research_prediction_rows,
    retrocast_rows,
)

DIVISION_I = ("FBS", "FCS")


def _escape(value: object) -> str:
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _num(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _pct(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}%"


def _iso(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _team_name(teams: dict[int, Team], team_id: int) -> str:
    team = teams.get(team_id)
    return team.name if team is not None else f"team-{team_id}"


def _game_label(game: Game, teams: dict[int, Team]) -> str:
    away = _team_name(teams, game.away_team_id)
    home = _team_name(teams, game.home_team_id)
    site = " vs " if game.neutral_site else " @ "
    return f"{away}{site}{home}"


def _metric_row(label: str, metrics: AccuracyMetrics) -> str:
    return "| " + " | ".join(
        [
            _escape(label),
            str(metrics.games),
            _pct(metrics.winner_accuracy),
            _num(metrics.spread_mae),
            _num(metrics.spread_rmse),
            _num(metrics.score_mae),
            _num(metrics.total_mae),
            _num(metrics.brier, 4),
            _pct(metrics.display_tie_rate),
            _pct(metrics.upset_hit_rate),
            _num(metrics.rank_result_correlation, 3),
        ]
    ) + " |"


def _metrics_table(samples: list[tuple[str, AccuracyMetrics]]) -> list[str]:
    lines = [
        "| Sample | Games | Winner | Margin MAE | Margin RMSE | Score MAE | Total MAE | Brier | Display ties | Upset hit | Rank/result corr |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(_metric_row(label, metrics) for label, metrics in samples)
    return lines


def _weekly_metrics(rows: list[tuple[object, Game]]) -> list[tuple[int, AccuracyMetrics]]:
    grouped: dict[int, list[tuple[object, Game]]] = defaultdict(list)
    for prediction, game in rows:
        grouped[game.week].append((prediction, game))
    return [(week, metrics_for_rows(grouped[week])) for week in sorted(grouped)]


def _append_weekly_metric_table(
    lines: list[str],
    label: str,
    rows: list[tuple[object, Game]],
) -> None:
    lines.extend(
        [
            f"### {label}",
            "",
            "| Week | Games | Winner | Margin MAE | Margin RMSE | Score MAE | Total MAE | Brier | Display ties |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    weekly = _weekly_metrics(rows)
    if not weekly:
        lines.append("| — | 0 | — | — | — | — | — | — | — |")
    for week, metrics in weekly:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(week),
                    str(metrics.games),
                    _pct(metrics.winner_accuracy),
                    _num(metrics.spread_mae),
                    _num(metrics.spread_rmse),
                    _num(metrics.score_mae),
                    _num(metrics.total_mae),
                    _num(metrics.brier, 4),
                    _pct(metrics.display_tie_rate),
                ]
            )
            + " |"
        )
    lines.append("")


def _independent_round(value: float) -> int:
    return max(0, int(math.floor(float(value) + 0.5)))


def _error_values(prediction: object, game: Game) -> dict[str, object]:
    actual_home = float(game.home_points)
    actual_away = float(game.away_points)
    actual_margin = actual_home - actual_away
    actual_total = actual_home + actual_away
    projected_home = float(getattr(prediction, "projected_home_points"))
    projected_away = float(getattr(prediction, "projected_away_points"))
    projected_margin = float(getattr(prediction, "projected_margin"))
    probability = float(getattr(prediction, "home_win_probability"))
    predicted_home_win = probability >= 0.5
    actual_home_win = actual_margin > 0.0
    raw_home = _independent_round(projected_home)
    raw_away = _independent_round(projected_away)
    return {
        "actual_margin": actual_margin,
        "actual_total": actual_total,
        "winner_correct": predicted_home_win == actual_home_win,
        "margin_ae": abs(projected_margin - actual_margin),
        "score_mae": (
            abs(projected_home - actual_home) + abs(projected_away - actual_away)
        )
        / 2.0,
        "total_ae": abs((projected_home + projected_away) - actual_total),
        "brier": (probability - (1.0 if actual_home_win else 0.0)) ** 2,
        "rounding_collision": (
            raw_home == raw_away and abs(projected_margin) > 1e-12
        ),
    }


def _detail_text(detail: dict | None) -> str:
    if not detail:
        return "—"
    parts = []
    for key in sorted(detail):
        value = detail[key]
        if isinstance(value, float):
            rendered = f"{value:.4f}".rstrip("0").rstrip(".")
        else:
            rendered = str(value)
        parts.append(f"{key}={rendered}")
    return _escape("; ".join(parts))


def _completed_division_i_games(session: Session, season: int) -> list[Game]:
    return list(
        session.scalars(
            select(Game)
            .where(
                Game.season == season,
                Game.completed.is_(True),
                Game.home_points.is_not(None),
                Game.away_points.is_not(None),
                Game.home_subdivision.in_(DIVISION_I),
                Game.away_subdivision.in_(DIVISION_I),
            )
            .order_by(Game.week, Game.start_time, Game.id)
        )
    )


def _count_by_week(rows: list[tuple[object, Game]]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for _, game in rows:
        counts[game.week] += 1
    return dict(counts)


def build_prediction_diagnostic_markdown(
    session: Session,
    *,
    season: int,
    app_version: str,
    model_version: str,
    predictor_version: str,
) -> str:
    """Build a read-only Markdown audit of the active prediction method."""
    generated_at = datetime.now(timezone.utc)
    teams = {team.id: team for team in session.scalars(select(Team)).all()}
    completed_games = _completed_division_i_games(session, season)
    retro_rows = retrocast_rows(session, season)
    official_rows = official_prediction_rows(session, season)
    shadow_rows = research_prediction_rows(session, season)

    retro_week_2 = [row for row in retro_rows if row[1].week == 2]
    retro_weeks_3_5 = [row for row in retro_rows if 3 <= row[1].week <= 5]
    retro_week_6_plus = [row for row in retro_rows if row[1].week >= 6]

    lines: list[str] = [
        f"# D1 Rank {season} prediction diagnostics",
        "",
        f"Generated: `{_iso(generated_at)}`  ",
        f"App: `{app_version}`  ",
        f"Ranking model: `{model_version}`  ",
        f"Predictor: `{predictor_version}`",
        "",
        "> This file is a read-only diagnostic export. It contains derived model inputs,",
        "> intermediate calculations, predictions, results, and error metrics. It does not",
        "> contain API keys, database credentials, or raw CFBD payloads.",
        "",
        "## Scope and interpretation",
        "",
        "- The leakage-safe retrocast sample contains completed **FBS/FCS vs FBS/FCS** games from Week 2 forward.",
        "- Week 1 is listed in coverage counts but cannot have a prior-week current-season retrocast.",
        "- Official locked predictions, retrocasts, and archived pre-promotion shadow predictions stay separate.",
        "- Compare models only on the same games. The Weeks 3-5 slice is included explicitly for reproduction work.",
        "- A displayed score is presentation only; accuracy calculations use the continuous projected scores/margin/probability.",
        "",
        "## Active hybrid formula",
        "",
        "```text",
        "rank_gap = away_rank - home_rank",
        "rank_margin = clamp(rank_gap * calibrated_rank_slope, +/- max_projected_margin)",
        "home_base = (home_offense + away_defense_allowance) / 2",
        "away_base = (away_offense + home_defense_allowance) / 2",
        "offdef_margin = home_base - away_base",
        f"hybrid_margin = {RANK_MARGIN_WEIGHT:.2f} * rank_margin + {OFFDEF_MARGIN_WEIGHT:.2f} * offdef_margin",
        "projected_total = home_base + away_base",
        "raw_home = (projected_total + hybrid_margin) / 2",
        "raw_away = (projected_total - hybrid_margin) / 2",
        "negative scores are equal-shifted so the modeled margin is preserved",
        "```",
        "",
        "### Constants",
        "",
        f"- Rank weight: `{RANK_MARGIN_WEIGHT:.2f}`",
        f"- Offense/defense weight: `{OFFDEF_MARGIN_WEIGHT:.2f}`",
        f"- Offense/defense shrinkage: `{DEFAULT_PRIOR_GAMES:.1f}` pseudo-games",
        f"- Rank-slope fallback: `{FALLBACK_POINTS_PER_RANK:.3f}` points/rank",
        f"- Rank-slope bounds: `{MIN_POINTS_PER_RANK:.3f}` to `{MAX_POINTS_PER_RANK:.3f}`",
        f"- Rank-margin cap: `+/-{MAX_PROJECTED_MARGIN:.1f}` points",
        "",
        "## Sample summary",
        "",
    ]

    lines.extend(
        _metrics_table(
            [
                ("Official locked active predictor", metrics_for_rows(official_rows)),
                ("Retrocast all Week 2+", metrics_for_rows(retro_rows)),
                ("Retrocast Week 2 only", metrics_for_rows(retro_week_2)),
                ("Retrocast Weeks 3-5 reproduction slice", metrics_for_rows(retro_weeks_3_5)),
                ("Retrocast Week 6+", metrics_for_rows(retro_week_6_plus)),
                ("Pre-promotion locked shadow", metrics_for_rows(shadow_rows)),
            ]
        )
    )
    lines.append("")

    completed_counts: dict[int, int] = defaultdict(int)
    for game in completed_games:
        completed_counts[game.week] += 1
    retro_counts = _count_by_week(retro_rows)
    official_counts = _count_by_week(official_rows)
    shadow_counts = _count_by_week(shadow_rows)
    all_weeks = sorted(
        set(completed_counts) | set(retro_counts) | set(official_counts) | set(shadow_counts)
    )

    lines.extend(
        [
            "## Week coverage",
            "",
            "| Week | Completed D-I vs D-I | Retrocast | Official locked | Shadow locked |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for week in all_weeks:
        lines.append(
            f"| {week} | {completed_counts.get(week, 0)} | {retro_counts.get(week, 0)} | "
            f"{official_counts.get(week, 0)} | {shadow_counts.get(week, 0)} |"
        )
    lines.append("")

    max_completed_week = max(completed_counts, default=1)
    lines.extend(
        [
            "## Calibration and scoring-profile state by source week",
            "",
            "Each source week is the information state used to predict the following week.",
            "",
            "| Source week | Snapshot | Rank slope | Residual SD | Calibration games | Calibration avg total | OD scoring games | Mean team points |",
            "|---:|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for source_week in range(1, max_completed_week):
        snapshot = get_snapshot(session, season, source_week)
        if snapshot is None:
            lines.append(
                f"| {source_week} | missing | — | — | — | — | — | — |"
            )
            continue
        calibration = fit_calibration(session, season, source_week)
        _, mean_team_points, scoring_games = fit_scoring_profiles(
            session,
            season,
            source_week,
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(source_week),
                    f"id {snapshot.id} / {snapshot.model_version}",
                    _num(calibration.rank_slope, 4),
                    _num(calibration.residual_sd),
                    str(calibration.sample_size),
                    _num(calibration.average_total),
                    str(scoring_games),
                    _num(mean_team_points),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("## Week-by-week metrics")
    lines.append("")
    _append_weekly_metric_table(lines, "Leakage-safe retrocast", retro_rows)
    _append_weekly_metric_table(lines, "Official locked active predictor", official_rows)
    _append_weekly_metric_table(lines, "Archived pre-promotion shadow", shadow_rows)

    retro_by_week: dict[int, list[tuple[object, Game]]] = defaultdict(list)
    for row in retro_rows:
        retro_by_week[row[1].week].append(row)

    lines.extend(
        [
            "## Per-game leakage-safe retrocast calculations",
            "",
            "`H/A` values are home then away. `Rank x w` and `OD x w` are the two weighted margin contributions. `Round collision` means ordinary independent rounding would have shown a tie even though the continuous margin was non-zero.",
            "",
        ]
    )
    header = (
        "| Game | Kickoff UTC | Prior wk | Ranks H/A | Gap | Slope | Rank M | Rank x w | "
        "Profile games H/A | H off/def | A off/def | Bases H/A | OD M | OD x w | "
        "Pred H/A | Display H/A | Actual H/A | P(H) | Pick | OK | Margin AE | Score MAE | "
        "Total AE | Brier | Round collision |"
    )
    separator = (
        "|---|---|---:|---|---:|---:|---:|---:|---|---|---|---|---:|---:|---|---|---|---:|---|:---:|---:|---:|---:|---:|:---:|"
    )
    for week in sorted(retro_by_week):
        lines.extend([f"### Week {week}", "", header, separator])
        for prediction, game in retro_by_week[week]:
            detail = getattr(prediction, "detail", {}) or {}
            errors = _error_values(prediction, game)
            display_home, display_away = display_scores_for_prediction(prediction)
            home_name = _team_name(teams, game.home_team_id)
            away_name = _team_name(teams, game.away_team_id)
            probability = float(getattr(prediction, "home_win_probability"))
            if probability > 0.5:
                pick = home_name
            elif probability < 0.5:
                pick = away_name
            else:
                pick = "Even"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _escape(_game_label(game, teams)),
                        _iso(game.start_time),
                        str(game.week - 1),
                        f"{_escape(getattr(prediction, 'home_rank', None))}/{_escape(getattr(prediction, 'away_rank', None))}",
                        _num(detail.get("rank_gap")),
                        _num(detail.get("rank_slope"), 4),
                        _num(detail.get("rank_margin")),
                        _num(detail.get("rank_contribution")),
                        f"{_escape(detail.get('home_profile_games'))}/{_escape(detail.get('away_profile_games'))}",
                        f"{_num(detail.get('home_offense'))}/{_num(detail.get('home_defense'))}",
                        f"{_num(detail.get('away_offense'))}/{_num(detail.get('away_defense'))}",
                        f"{_num(detail.get('home_base'))}/{_num(detail.get('away_base'))}",
                        _num(detail.get("offdef_margin")),
                        _num(detail.get("offdef_contribution")),
                        f"{_num(getattr(prediction, 'projected_home_points'))}/{_num(getattr(prediction, 'projected_away_points'))}",
                        f"{display_home}/{display_away}",
                        f"{game.home_points}/{game.away_points}",
                        _pct(probability),
                        _escape(pick),
                        "Y" if errors["winner_correct"] else "N",
                        _num(errors["margin_ae"]),
                        _num(errors["score_mae"]),
                        _num(errors["total_ae"]),
                        _num(errors["brier"], 4),
                        "Y" if errors["rounding_collision"] else "N",
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(
        [
            "## Official locked active-predictor rows",
            "",
            "These are the immutable active-predictor rows that actually existed before kickoff and later became official. Stored model detail is included exactly as available on each row.",
            "",
            "| Week | Game | Source wk | Created UTC | Locked UTC | Ranks H/A | Pred H/A | Display H/A | Margin | P(H) | Actual H/A | OK | Margin AE | Score MAE | Total AE | Brier | Stored model detail |",
            "|---:|---|---:|---|---|---|---|---|---:|---:|---|:---:|---:|---:|---:|---:|---|",
        ]
    )
    for prediction, game in sorted(
        official_rows,
        key=lambda row: (row[1].week, row[1].start_time or datetime.min, row[1].id),
    ):
        errors = _error_values(prediction, game)
        display_home, display_away = display_scores_for_prediction(prediction)
        source_week = prediction.ranking_snapshot.week
        lines.append(
            "| "
            + " | ".join(
                [
                    str(game.week),
                    _escape(_game_label(game, teams)),
                    str(source_week),
                    _iso(prediction.created_at),
                    _iso(prediction.locked_at),
                    f"{_escape(prediction.home_rank)}/{_escape(prediction.away_rank)}",
                    f"{_num(prediction.projected_home_points)}/{_num(prediction.projected_away_points)}",
                    f"{display_home}/{display_away}",
                    _num(prediction.projected_margin),
                    _pct(prediction.home_win_probability),
                    f"{game.home_points}/{game.away_points}",
                    "Y" if errors["winner_correct"] else "N",
                    _num(errors["margin_ae"]),
                    _num(errors["score_mae"]),
                    _num(errors["total_ae"]),
                    _num(errors["brier"], 4),
                    _detail_text(prediction.model_detail),
                ]
            )
            + " |"
        )
    if not official_rows:
        lines.append("| — | No completed official active-predictor rows | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |")
    lines.append("")

    lines.extend(
        [
            "## Archived pre-promotion shadow rows",
            "",
            "| Week | Game | Source wk | Created UTC | Locked UTC | Pred H/A | Margin | P(H) | Actual H/A | OK | Stored model detail |",
            "|---:|---|---:|---|---|---|---:|---:|---|:---:|---|",
        ]
    )
    for prediction, game in sorted(
        shadow_rows,
        key=lambda row: (row[1].week, row[1].start_time or datetime.min, row[1].id),
    ):
        errors = _error_values(prediction, game)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(game.week),
                    _escape(_game_label(game, teams)),
                    str(prediction.ranking_snapshot.week),
                    _iso(prediction.created_at),
                    _iso(prediction.locked_at),
                    f"{_num(prediction.projected_home_points)}/{_num(prediction.projected_away_points)}",
                    _num(prediction.projected_margin),
                    _pct(prediction.home_win_probability),
                    f"{game.home_points}/{game.away_points}",
                    "Y" if errors["winner_correct"] else "N",
                    _detail_text(prediction.model_detail),
                ]
            )
            + " |"
        )
    if not shadow_rows:
        lines.append("| — | No completed locked shadow rows | — | — | — | — | — | — | — | — | — |")
    lines.append("")

    lines.extend(
        [
            "## Diagnostic checklist",
            "",
            "When comparing this export with an earlier experiment, verify these before changing weights:",
            "",
            "1. same weeks and same game IDs/sample size;",
            "2. same prior-week ranking snapshot for every game;",
            "3. same FBS/FCS inclusion rules;",
            "4. same three-pseudo-game offense/defense shrinkage;",
            "5. same season mean used for shrinkage;",
            "6. same 40/60 margin weights;",
            "7. same rank-slope calibration sample and bounds;",
            "8. same handling of teams with no prior scoring profile;",
            "9. same continuous-score normalization before display rounding;",
            "10. compare headline percentages only after the paired sample is identical.",
            "",
        ]
    )

    return "\n".join(lines)
