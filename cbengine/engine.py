"""Explicit dated cashflows, ACT/365F annual compounding, clause evidence."""
import math
from decimal import Decimal
from datetime import date


def iso_date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("dates must use YYYY-MM-DD")
    return value


def source(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("source must be a nonempty string")
    return value


def finite(value, name, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"{name}: invalid number")
    return number


def year_fraction(start, end):
    return (date.fromisoformat(iso_date(end)) - date.fromisoformat(iso_date(start))).days / 365


def spot(curve, t):
    points = [(finite(p[0], "tenor", True), finite(p[1], "rate")) for p in curve]
    if not points or any(r <= -1 for _, r in points):
        raise ValueError("curve must have positive tenors and rates > -1")
    if any(points[i][0] >= points[i+1][0] for i in range(len(points)-1)):
        raise ValueError("curve tenors must be strictly increasing")
    if t < points[0][0] or t > points[-1][0]:
        raise ValueError("cashflow tenor outside curve: extrapolation refused")
    for (a, ra), (b, rb) in zip(points, points[1:]):
        if a <= t <= b:
            return ra + (rb-ra) * (t-a) / (b-a)
    return points[-1][1]


def present_value(flows, rate):
    return sum(amount * math.exp(-t * math.log1p(rate)) for t, amount in flows)


def yield_rate(price, flows):
    """Unique IRR for strictly positive future cashflows; annual effective yield."""
    price = finite(price, "price", True)
    flows = [(finite(t, "cashflow time", True), finite(a, "cashflow amount", True)) for t, a in flows]
    if not flows or any(t <= 0 or amount <= 0 for t, amount in flows):
        raise ValueError("IRR requires positive future cashflows")
    # Solve in log(1+y), avoiding singularity at y=-1.
    def value(log_rate):
        total = 0.0
        for t, amount in flows:
            exponent = -t * log_rate
            if exponent > 700:
                return math.inf
            total += amount * math.exp(exponent)
        return total
    lo, hi = -1.0, 1.0
    for _ in range(64):
        if value(lo) >= price:
            break
        lo *= 2
    for _ in range(64):
        if value(hi) <= price:
            break
        hi *= 2
    if value(lo) < price or value(hi) > price:
        raise ValueError("yield root not bracketed")
    for _ in range(180):
        mid = (lo+hi)/2
        if value(mid) > price:
            lo = mid
        else:
            hi = mid
    try:
        return math.expm1((lo+hi)/2)
    except OverflowError as exc:
        raise ValueError("yield exceeds numerical range") from exc


def clause_state(clause, observations, as_of):
    required = ("source", "window", "count", "ratio", "direction", "rolling",
                "active_from", "active_until", "reset_on")
    if any(k not in clause for k in required):
        raise ValueError("clause missing source or explicit parameters")
    source(clause['source'])
    w, c = clause["window"], clause["count"]
    if type(w) is not int or type(c) is not int or not 1 <= c <= w:
        raise ValueError("clause requires integer 1 <= count <= window")
    if clause["rolling"] is not True:
        raise ValueError("v0.1 only supports explicitly rolling windows")
    if clause["direction"] not in ("above", "below"):
        raise ValueError("direction must be above or below")
    ratio = finite(clause["ratio"], "ratio", True)
    inclusive=clause.get('inclusive',True)
    if type(inclusive) is not bool: raise ValueError('inclusive must be boolean')
    start, end = clause["active_from"], clause["active_until"]
    for d in (start, end, as_of):
        iso_date(d)
    if start > end:
        raise ValueError("clause active dates reversed")
    resets = clause["reset_on"]
    if not isinstance(resets, list):
        raise ValueError("reset_on must be explicit date list")
    for d in resets:
        iso_date(d)
    boundary = max([start] + [d for d in resets if d <= as_of])
    relevant = [o for o in observations if boundary <= o["date"] <= min(as_of, end)]
    window = relevant[-w:]
    hits = []
    for o in window:
        # Each historical observation carries the conversion price valid THAT day.
        s = finite(o["stock_price"], "stock_price", True)
        k = finite(o["conversion_price"], "conversion_price", True)
        barrier=Decimal(str(k))*Decimal(str(ratio))
        observed=Decimal(str(s))
        hits.append((observed>=barrier if inclusive else observed>barrier) if clause['direction']=='above'
                    else (observed<=barrier if inclusive else observed<barrier))
    n = sum(hits)
    active = start <= as_of <= end
    # Counts are conditional on supplied history. Never turn missing history
    # into a definitive negative result or treat stale history as current.
    fresh = bool(window) and window[-1]['date'] == as_of
    met = (n >= c) if active and fresh else False if not active else None
    if active and fresh and n < c and len(window) < w:
        met = None
    status = 'inactive' if not active else 'condition_met' if met is True else 'unknown' if met is None else 'condition_not_met'
    return {"count": n, "required": c, "window": w, "observations": len(window),
            "trigger_condition_met": met, "status": status, "active": active,
            "latest_observation": window[-1]['date'] if window else None,
            "history_current": fresh,
            "history_complete": len(window) == w,
            "comparison": ('>=' if inclusive else '>') if clause['direction']=='above' else ('<=' if inclusive else '<'),
            "comparison_basis":'explicit' if 'inclusive' in clause else 'legacy-inclusive-assumption',
            "days_to_fill_window": w-len(window),
            "oldest_observation": window[0]["date"] if window else None,
            "next_observation_expels_oldest": len(window) == w,
            "source": clause["source"],
            "note": "滚动窗口满后每日移出最旧记录；满足条件不代表发行人已行使权利。"}


def diagnose(data):
    if not isinstance(data, dict):
        raise ValueError('security input must be an object')
    as_of = data["as_of"]
    iso_date(as_of)
    if not isinstance(data['code'], str) or not data['code'].strip():
        raise ValueError('code must be a nonempty string')
    price = finite(data["dirty_price"], "dirty_price", True)
    stock = finite(data["stock_price"], "stock_price", True)
    conversion = finite(data["conversion_price"], "conversion_price", True)
    source(data.get('cashflow_source'))
    source(data.get('curve_source'))
    tax = finite(data["coupon_tax_rate"], "coupon_tax_rate")
    if not 0 <= tax <= 1:
        raise ValueError("coupon_tax_rate outside [0,1]")
    if not data.get("cashflows"):
        raise ValueError("explicit future cashflows required")
    rows, flows, taxed = [], [], []
    previous = as_of
    for cf in data["cashflows"]:
        if cf["date"] <= previous:
            raise ValueError("cashflows must be future and strictly date ordered")
        previous = cf["date"]
        t = year_fraction(as_of, cf["date"])
        coupon = finite(cf["coupon"], "coupon")
        redemption = finite(cf["redemption"], "redemption")
        # redemption must EXCLUDE coupon; tax is explicit, never inferred.
        redemption_tax = finite(cf["redemption_tax"], "redemption_tax")
        if min(coupon, redemption, redemption_tax) < 0 or redemption_tax > redemption:
            raise ValueError("invalid cashflow components")
        gross, net = coupon+redemption, coupon*(1-tax)+redemption-redemption_tax
        if gross <= 0 or net <= 0:
            raise ValueError("cashflows must be positive")
        z = spot(data["discount_curve"], t)
        pv = gross/(1+z)**t
        rows.append({"date": cf["date"], "years": t, "gross": gross, "net": net,
                     "spot": z, "pv": pv})
        flows.append((t, gross))
        taxed.append((t, net))
    floor = sum(r["pv"] for r in rows)
    duration = sum(r["years"]*r["pv"] for r in rows)/floor
    modified = sum(r["years"]*r["pv"]/(1+r["spot"]) for r in rows)/floor
    convexity = sum(r["years"]*(r["years"]+1)*r["pv"]/(1+r["spot"])**2 for r in rows)/floor
    sensitivity = {}
    for shift in (-0.02, -0.01, 0.01, 0.02):
        if any(r["spot"]+shift <= -1 for r in rows):
            raise ValueError("curve shift invalid")
        actual = sum(r["gross"]/(1+r["spot"]+shift)**r["years"] for r in rows)
        approx = floor*(1-modified*shift+0.5*convexity*shift**2)
        sensitivity[str(round(shift*10000))] = {"price": actual, "approximation": approx,
                                               "approximation_error": approx-actual}
    observations = data.get("observations", [])
    last = ""
    for o in observations:
        iso_date(o["date"])
        finite(o["stock_price"], "historical stock price", True)
        finite(o["conversion_price"], "historical conversion price", True)
        if not last < o["date"] <= as_of:
            raise ValueError("observations must be ordered, unique, no future dates")
        last = o["date"]
    clauses = data.get("clauses")
    if not isinstance(clauses, dict) or set(clauses) != {"call", "put", "reset"}:
        raise ValueError("call/put/reset clauses required; use null for absent clause")
    states = {name: clause_state(c, observations, as_of) if c is not None else
              {"absent": True} for name, c in clauses.items()}
    yields = {"maturity": {"gross": yield_rate(price, flows), "net": yield_rate(price, taxed)}}
    for name, scenario in data.get("exit_scenarios", {}).items():
        if name not in ("call", "put"):
            raise ValueError("exit scenarios require call/put name and source")
        source(scenario.get('source'))
        if clauses[name] is None:
            raise ValueError('exit scenario conflicts with absent clause')
        t = year_fraction(as_of, scenario["date"])
        if not 0 < t <= rows[-1]["years"]:
            raise ValueError("exit scenario must be future and before maturity")
        gross = finite(scenario["gross_payment"], "gross_payment", True)
        net = finite(scenario["net_payment"], "net_payment", True)
        if net > gross:
            raise ValueError("net exit payment exceeds gross")
        before_gross = [f for f in flows if f[0] < t]
        before_net = [f for f in taxed if f[0] < t]
        yields[name] = {"gross": yield_rate(price, before_gross+[(t, gross)]),
                        "net": yield_rate(price, before_net+[(t, net)]),
                        "conditional": True, "source": scenario["source"]}
    parity = 100*stock/conversion
    warnings = ["教学数据" ] if data.get("is_demo") else []
    warnings += ["债底不是保证兑付价；本版未建模违约、流动性和转股期权。",
                 "条款计数依赖输入交易日记录完整性，本版不核验交易所日历。"]
    if len(yields) < 3:
        warnings.append("退出场景不全，YTW仅为已提供场景最小值，不是完整最差收益率。")
    if any(not s.get("history_complete", True) for s in states.values()):
        warnings.append("条款窗口历史不足，未达门槛不能据此认定未触发。")
    if any(s.get('status') == 'unknown' for s in states.values()):
        warnings.append('条款状态未知：历史不足或末条观测不是估值日；计数仅供核对。')
    if any(s.get('comparison_basis')=='legacy-inclusive-assumption' for s in states.values()):
        warnings.append('旧输入未声明是否包含等号，暂按含等号计算；须核对原文并补inclusive参数。')
    promise = data.get("no_call_until")
    if promise:
        iso_date(promise)
        source(data.get('no_call_source'))
    if states["call"].get("trigger_condition_met") and not (promise and as_of <= promise):
        warnings.append("强赎条件已满足且无有效不强赎承诺；核对公告及操作期限。")
    lower = None
    if data.get("reset_floor_inputs"):
        p = data["reset_floor_inputs"]
        source(p.get('source'))
        lower = max(finite(v, "reset floor", True) for v in p["applicable_floors"])
        lower = {"minimum_conversion_price": lower, "parity_if_reset_to_floor": 100*stock/lower,
                 "reduction_possible": lower < conversion, "source": p["source"]}
    return {"code": data["code"], "as_of": as_of, "model_level": "L1",
            "conventions": "每100元面值；输入全价；ACT/365F；年复利；利率为小数",
            "cashflow_source": data["cashflow_source"], "curve_source": data["curve_source"],
            "dirty_price": price, "bond_floor": floor, "conversion_value": parity,
            "bond_premium": price/floor-1, "conversion_premium": price/parity-1,
            "distance_to_floor": (price-floor)/price,
            "duration": duration, "modified_duration_parallel": modified,
            "convexity_parallel": convexity, "dv01": floor*modified*0.0001,
            "sensitivity_bps": sensitivity, "cashflows": rows, "yields": yields,
            "minimum_provided_yield": {k: min(v[k] for v in yields.values()) for k in ("gross", "net")},
            "clauses": states, "no_call_until": promise,
            "no_call_source": data.get("no_call_source"), "reset_floor": lower,
            "warnings": warnings}
