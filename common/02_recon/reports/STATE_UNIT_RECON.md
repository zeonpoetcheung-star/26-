# A-2 State and Unit Contract

## Unambiguous quantities

- Storage maximum capacity: 12,000 kWh.
- Allowed state range: 1,200-10,800 kWh; usable band: 9,600 kWh.
- Initial state: 6,000 kWh at 2025-01-01 0:00.
- Maximum charge/discharge power: 5,000 kW.
- Ten-minute duration: 1/6 h.
- Rated ten-minute transfer before any efficiency convention: 5,000 x 1/6 = 833.333333 kWh.
- The statement gives charge/discharge efficiency as 90% without fixing its mathematical decomposition.

## State-time boundary

- A 144-interval 0:00-24:00 convention naturally has 145 state-boundary points.
- P1 explicitly requires S(0:00)=S(24:00).
- P2/P3/P4 do not explicitly repeat daily equality; the only numerical initial SOC is at 2025-01-01 0:00.
- Efficiency side, battery/grid-side quantities, daily reset versus cross-day propagation, and terminal treatment remain unresolved for A-4.
