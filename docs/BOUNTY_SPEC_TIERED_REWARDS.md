# Tiered bounty-spec reward semantics

Some bounties offer multiple deliverable types at different rates. A single scalar `reward_rtc` is not sufficient to describe those bounties without ambiguity.

## Rule

When the human-facing bounty defines more than one reward tier, machine-readable metadata must preserve the same tier mapping. Automation must not infer that one scalar reward applies to every package type.

For example, if a bounty pays Type A = 40 RTC, Type B = 15 RTC, Type C = 15 RTC, and Type D = 8 RTC, do not encode only:

```yaml
reward_rtc: 40
per: per-package
```

That representation can cause payout, discovery, or agent tooling to price B/C/D packages at the Type A rate.

Prefer an explicit mapping:

```yaml
paid: true
reward_rtc:
  A: 40
  B: 15
  C: 15
  D: 8
per: per-package
submit: [comment, email]
```

If the current parser accepts only a scalar `reward_rtc`, keep the scalar for backward compatibility but add a machine-readable tier field and treat the human-facing table/title as authoritative until parser support lands:

```yaml
paid: true
reward_rtc: 40
reward_tiers:
  A: 40
  B: 15
  C: 15
  D: 8
per: per-package
submit: [comment, email]
```

## Caps

A cap must say what it counts. For heterogeneous rounds, avoid a bare aggregate such as `cap: 30` when the bounty actually means separate limits per package type. Prefer:

```yaml
caps:
  A: 5
  B: 5
  C: 10
  D: 10
```

This prevents an agent from interpreting a sum of per-tier slots as a per-person cap, or vice versa.

## Validation checklist

Before publishing or editing a tiered bounty:

1. Compare the title, reward table, prose, and `bounty-spec`.
2. Verify every package/deliverable type has the same reward in both human and machine-readable representations.
3. Verify caps have an explicit scope: per-person, per-item, per-tier, or pool-wide.
4. If a legacy parser forces a lossy scalar, document which field is authoritative and include the full tier mapping in a separate machine-readable field.
5. Update both representations in the same change when rates or caps change.

The goal is boring but important: humans and payout/discovery automation should calculate the same reward from the same bounty.