# Business Summary

## 1. Why This Problem Matters

Congestion pricing changes the economics of entering Manhattan's core. For a ride-hailing platform, the material question is not simply whether orders move. It is whether supply should move too, whether passengers absorb the cost, and whether drivers still earn enough to accept affected routes.

## 2. Data and Method

The project uses 2024-2025 NYC TLC trip records, with High Volume FHV as the principal platform proxy. It constructs trip-level policy features, zone-hour panels and OD panels. Treated core zones are compared with configured control zones before and after the policy start; an event-study view checks whether relative movement was already visible before the intervention.

## 3. Main Findings

Results are generated from the current data run rather than hard-coded into this document. The relevant outputs identify demand changes by zone and hour, likely spillover zones, changed OD routes and routes where fare changes do not pass through to driver pay.

## 4. Causal Evidence

Difference-in-Differences estimates compare treated-zone change with control-zone change while accounting for zone, hour and weekday effects. Event-study estimates make the time pattern visible. The counterfactual model is deliberately secondary: it describes an expected-demand benchmark, while the quasi-experimental comparison carries the causal interpretation.

## 5. Business Recommendations

- Reallocate supply toward boundary zones only when the spillover score and post-policy volume both support it.
- Test targeted driver incentives on routes where rider price rises while driver-pay-per-minute does not.
- Treat airport and peak windows as separate operating surfaces rather than applying one citywide policy.
- Use a controlled rollout and monitor acceptance, idle time and fulfillment before scaling any incentive.

## 6. Limitations

TLC records do not reveal platform-wide supply, the exact path through the congestion zone, or all competing mobility shocks. The configured zone groups are transparent proxies and should be stress-tested. A causal estimate is conditional on the credibility of the control group and pre-trend evidence.

## 7. What I Would Improve Next

I would run the full Spark pipeline over the full event window, add weather and transit disruptions, define treatment with geospatial CRZ polygons, cluster uncertainty by zone, and link recommendations to a prospective A/B test.
