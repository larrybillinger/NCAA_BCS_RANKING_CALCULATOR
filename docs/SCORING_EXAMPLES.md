# Current-Season Scoring Examples

These examples describe the production `division_i_weighted_v4` model.

For illustration, these examples use a 267-team Division I pool, so the neutral first-game scoring rank is 134.

## FBS home win over FCS

FBS Team 71, FCS Team 3.

```text
Opponent Rank Points = 268 - 134 = 134
Scoring Margin       = +68
Site Adjustment      = 0
Normal Score         = 202
FBS Multiplier       = 1.0
Final Score          = 202
```

There is no +10 win bonus.

## FCS road loss to FBS

Same game from the FCS team's perspective:

```text
Opponent Rank Points = -134
Scoring Margin       = -68
Site Adjustment      = 0
Normal Score         = -202
FCS Multiplier       = 0.5
Final Score          = -101
```

An away loss does not receive the extra -7 penalty.

## FBS road win

A visiting FBS team beats an FBS opponent whose prior-week scoring rank is #40, 31-17.

```text
Opponent Rank Points = 268 - 40 = 228
Scoring Margin       = +14
Road-Win Adjustment  = +7
Final Score          = 249
```

## FBS home loss

A home FBS team loses 17-31 to an FBS opponent whose prior-week scoring rank is #40.

```text
Opponent Rank Points = -40
Scoring Margin       = -14
Home-Loss Adjustment = -7
Final Score          = -61
```

## FCS road upset over FBS

A visiting FCS team beats the prior-week #40 FBS team 31-17.

```text
Opponent Rank Points = 228
Scoring Margin       = +14
Road-Win Adjustment  = +7
Normal Score         = 249
FCS win over FBS     = 100%
Final Score          = 249
```

## FCS home loss to FBS

An FCS team loses 17-31 at home to the prior-week #40 FBS team.

```text
Opponent Rank Points = -40
Scoring Margin       = -14
Rank + Margin        = -54
FCS Multiplier       = 0.5
Scaled Rank + Margin = -27
Home-Loss Adjustment = -7
Final Score          = -34
```

## FCS vs FCS

An FCS team beats another FCS team 30-10 at a neutral site while the opponent's scoring rank is 40.

```text
Opponent Rank Points = 268 - 40 = 228
Scoring Margin       = +20
Site Adjustment      = 0
Normal Score         = 248
FCS-vs-FCS Multiplier= 0.5
Scaled Rank + Margin = 124
Site Adjustment      = 0
Final Score          = 124
```

## Explicit Division I percentages

```text
FBS vs FBS       = 100%
FBS vs FCS       = 100%
FCS vs FCS       = 50%
FCS loss to FBS  = 50%
FCS win over FBS = 100%
```

FCS is part of Division I; the labels are written separately only to make the production multiplier unambiguous.
