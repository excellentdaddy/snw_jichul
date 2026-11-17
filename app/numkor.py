"""숫자 → 한글 금액 (엑셀 NUMBERSTRING(n, 1) 과 같은 결과)."""

DIGITS = "영일이삼사오육칠팔구"
SMALL = ["", "십", "백", "천"]
BIG = ["", "만", "억", "조", "경"]


def numberstring(n: int) -> str:
    n = int(n)
    if n == 0:
        return "영"
    neg = n < 0
    n = abs(n)
    parts = []
    big = 0
    while n > 0:
        group = n % 10000
        n //= 10000
        if group:
            s = ""
            for i in range(3, -1, -1):
                d = (group // (10 ** i)) % 10
                if d:
                    s += DIGITS[d] + SMALL[i]
            parts.append(s + BIG[big])
        big += 1
    out = "".join(reversed(parts))
    return ("마이너스" if neg else "") + out


if __name__ == "__main__":
    for v in (10000, 352000, 1520000, 5847600, 33000000, 66000000, 110, 1):
        print(v, numberstring(v))
