# Nonlinear Throughput Response in Distributed Assembly

### A. Researcher B. Coauthor

## Abstract

We examine throughput under varying load. A nonlinear response appears above a critical rate, consistent with standard queueing bounds. The effect is stable across three independent samples and is not an artifact of measurement granularity.

## 1 Introduction

Prior work has focused on static loads, which cannot separate capacity constraints from scheduling artifacts because the two produce observationally equivalent steady states. We extend the analysis to dynamic regimes, where the distinction becomes identifiable. Our contribution is threefold, and each part depends on an apparatus whose calibration is unusually delicate, so we describe it at length before turning to the estimation strategy that occupies the remainder of this section.

## 2 Model

Let *λ* denote the arrival rate and *µ* the service rate. The utilization is

$$
ρ = λ µ, 0 < ρ < 1. (1)
$$

Expected queue length follows the standard result

$$
E[L] = ρ2 1 −ρ + ρ = ∞ X n=1 n(1 −ρ)ρn. (2)
$$

The bound is tight as *ρ →*1<sup>−</sup>, which motivates the design below.

## 3 Method

Three conditions were run:

- Baseline: nominal scheduling, no preemption.
- Treatment A: preemptive scheduling enabled.
- Treatment B: hybrid policy.

Each condition comprised roughly 120 trials, randomized within block.[^1]

## 4 Results

Table 1 reports descriptives by condition. Both treatments exceed baseline, and Treatment A exceeds Treatment B.

| Condition | N | Mean | SD |
| --- | --- | --- | --- |
| Baseline | 120 | 41.2 | 3.4 |
| Treatment A | 118 | 52.7 | 4.1 |
| Treatment B | 121 | 48.9 | 3.9 |
| Pooled | 359 | 47.6 | 6.2 |

*Table 1: Throughput by condition, pooled across blocks.*

## 5 Discussion

If the constraint were purely physical, preemption should not help; that it does help implies a scheduling component.[^2]Future work should examine attenuation at higher loads.

[^1]: We thank two anonymous reviewers for helpful comments.

[^2]: Replication materials are archived at the project site.
