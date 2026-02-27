# Proposal: Dynamic Strike Window for Option Chain Fetching

## Why
Currently, the `OptionChainBuilder` fetches the entire 0DTE option chain for SPY, which can contain 120+ individual option contracts. While comprehensive, this approach:
1.  **API Overhead**: Requests a large amount of data from Longport API, potentially hitting rate limits or increasing latency.
2.  **Computational Noise**: Downstream calculations (GEX, Vanna, Charm) process deep out-of-the-money or deep in-the-money contracts that contribute negligible informational value to intraday strategies.
3.  **Memory Footprint**: Stores unnecessary historical data for inactive strikes.

## What
Implement a **Dynamic Strike Window** that follows the SPY spot price.

## Capabilities
## What Changes
- **Capability: Batch Volume Research**: Implement a one-time or periodic scan of a wider range (+/- 70 points) to generate a volume distribution profile.
- **Capability: Data-Driven Window Optimization**: Use the volume distribution profile to dynamically adjust the active window size based on where the "Liquidity Walls" or high-volume activity reside.
- **Improved Focus**: Calculations will focus on the most delta-sensitive and gamma-heavy "active" region of the chain, informed by current market liquidity.
