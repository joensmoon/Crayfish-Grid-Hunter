# Technical Indicator Calculations

This document outlines the formulas and methodologies for all indicators and scoring systems used in the Grid Hunter skill.

## Average True Range (ATR)

ATR is a technical analysis volatility indicator. It is typically derived from the 14-day simple moving average of a series of true range indicators.

**True Range (TR)** is the greatest of the following:

*   Current High less the current Low
*   The absolute value of the current High less the previous Close
*   The absolute value of the current Low less the previous Close

**ATR Formula**:

`ATR = (1/n) * SUM(TR_i for i=1 to n)` where `n` = number of periods (typically 14).

**Interpretation for Grid Trading**: A higher ATR indicates greater price movement per period. Grid Hunter uses ATR to determine whether a token has sufficient volatility to generate meaningful grid trading profits.

## Relative Strength Index (RSI)

RSI is a momentum oscillator that measures the speed and change of price movements. RSI oscillates between zero and 100.

**RSI Formula**: `RSI = 100 - [100 / (1 + RS)]` where `RS = Average Gain / Average Loss`.

**Calculation Steps (Wilder Smoothing Method)**:

1.  Calculate the price change for each period: `change = close[i] - close[i-1]`
2.  Separate gains (positive changes) and losses (absolute value of negative changes).
3.  **First Average**: Calculate the simple average of the first `n` gains and losses:
    *   `first_avg_gain = SUM(gains[0..n-1]) / n`
    *   `first_avg_loss = SUM(losses[0..n-1]) / n`
4.  **Subsequent Averages** (Wilder Smoothing): For each subsequent period:
    *   `avg_gain = (prev_avg_gain * (n - 1) + current_gain) / n`
    *   `avg_loss = (prev_avg_loss * (n - 1) + current_loss) / n`
5.  Calculate RS: `RS = avg_gain / avg_loss`
6.  Calculate RSI: `RSI = 100 - (100 / (1 + RS))`

**Why Wilder Smoothing?**

The Wilder smoothing method gives more weight to recent price changes compared to the simple average method. This produces RSI values that are more responsive to current market conditions, which is critical for grid trading where timely entry/exit decisions matter. The simple average method can produce misleadingly stable RSI values (e.g., always near 50) when the data window is short.

**Interpretation for Grid Trading**:

| RSI Range | Interpretation | Grid Trading Action |
| :--- | :--- | :--- |
| 30-70 | Ideal oscillating range | Best for grid trading |
| 35-65 | Optimal sweet spot | Highest grid score bonus |
| < 30 | Oversold condition | Avoid opening new grid positions |
| > 70 | Overbought condition | Avoid opening new grid positions |

## Bollinger Bands

Bollinger Bands characterize the prices and volatility over time of a financial instrument.

**Bollinger Bands Formula**:

*   **Middle Band**: 20-period simple moving average (SMA)
*   **Upper Band**: 20-period SMA + (20-period standard deviation of price x 2)
*   **Lower Band**: 20-period SMA - (20-period standard deviation of price x 2)

**Interpretation for Grid Trading**: The Upper and Lower bands define the natural price oscillation range. Grid range should be set within or near the Bollinger Band boundaries. A narrowing band width suggests decreasing volatility (potential breakout ahead).

## Trend Slope

A simple linear regression determines the trend of the price over a period.

**Formula**: `y = mx + c` where `y` = price, `x` = time (period index), `m` = slope of the trend line.

The slope is normalized as a percentage of the average price: `normalized_slope = (m / avg_price) * 100`.

| Slope Range | Interpretation | Grid Suitability |
| :--- | :--- | :--- |
| \|slope\| < 0.5% | Strong sideways signal | Best for grid (score +30) |
| \|slope\| < 1.0% | Mild trend | Acceptable (score +20) |
| \|slope\| < 2.0% | Moderate trend | Marginal (score +10) |
| \|slope\| > 2.0% | Strong trend | Avoid grid trading |

## Volatility

Price volatility is calculated as the percentage range of price movement over the analysis period.

**Formula**: `volatility = ((max_high - min_low) / midpoint) * 100` where `midpoint = (max_high + min_low) / 2`.

| Volatility Range | Interpretation | Grid Suitability |
| :--- | :--- | :--- |
| 5-20% | Ideal range | Best for grid (score +30) |
| 3-5% | Low volatility | Acceptable (score +15) |
| < 3% | Too low | Grid profits will be minimal — excluded |
| > 25% | Too high | Increased risk of stop-loss triggers |

## Composite Grid Score

Grid Hunter assigns a composite score (0-115) to each candidate token based on multiple factors. The scoring breakdown is as follows:

| Factor | Max Points | Criteria |
| :--- | :--- | :--- |
| Volatility | 30 | 5-20% volatility = 30 pts; 3-5% = 15 pts |
| RSI | 30 | 35-65 = 30 pts; 30-35 or 65-70 = 15 pts |
| Trend Slope | 30 | \|slope\| < 0.5% = 30 pts; < 1.0% = 20 pts; < 2.0% = 10 pts |
| Range Quality | 10 | Range percentage > 5% = 10 pts |
| Smart Money | 15 | BUY signal detected = 15 pts (bonus) |
| Security Audit | 5 (bonus) | SAFE status = 5 pts (bonus, deducted if DANGEROUS) |

A score of 70 or above is considered a strong grid trading candidate. Scores below 40 are generally not recommended.

## Breakout Alert Thresholds

Grid Hunter monitors active grid positions for potential breakout conditions using the following thresholds:

| Condition | Threshold | Alert Level |
| :--- | :--- | :--- |
| Price near range boundary | Within 10% of upper/lower bound | WARNING |
| Volume spike | 24h volume > 200% of average | HIGH |
| Price change | \|24h change\| > 5% | HIGH |
| Combined (price + volume) | Both conditions met | CRITICAL |


