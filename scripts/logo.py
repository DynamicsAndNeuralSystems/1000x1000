"""The 1000×1000 logo (design canvas board 14, "triple orbit, pastel zeros"): the three zeros of each 1000 are one
trajectory tracing three touching ovals, drawn as an open trail that fades towards its tail and stops just short
of a moving point, over the website's class pastels. Writes site/logo.svg (wordmark), site/favicon.svg (the 000
mark) and site/prints the header wordmark (drawn in currentColor) for index.html."""
import math
F=lambda v: f"{v:.1f}".rstrip('0').rstrip('.')
def triple_path(x0, rx=27, ry=46, cy=51, n_per=160):
    """one trajectory tracing three touching ovals: 000"""
    c=[x0+rx, x0+3*rx, x0+5*rx]
    P=lambda i,f: (c[i]+rx*math.sin(f), cy-ry*math.cos(f))
    segs=[(1,1.5*math.pi,0.5*math.pi,0.5),(2,1.5*math.pi,3.5*math.pi,1),(1,0.5*math.pi,-0.5*math.pi,0.5),(0,0.5*math.pi,2.5*math.pi,1)]
    pts=[]
    for i,a,b,frac in segs:
        m=int(n_per*frac)
        pts+= [P(i,a+(b-a)*k/m) for k in range(m)]
    return pts
def trail(pts, col, sw, start_frac=0.27, gap=0.05, nseg=10, dot=6.5):
    """draw the closed path as an open, fading trail ending at a head dot"""
    N=len(pts); s=int(start_frac*N)
    seq=pts[s:]+pts[:s]                 # start just after the head, go round
    L=int(N*(1-gap)); seq=seq[:L]       # leave a gap before the head so it never closes
    out=[]
    for k in range(nseg):
        a=k*L//nseg; b=min(L-1,(k+1)*L//nseg)
        seg=seq[a:b+1]
        out.append(f'<polyline points="{" ".join(F(x)+","+F(y) for x,y in seg)}" fill="none" stroke="{col}" stroke-width="{F(sw)}" stroke-linecap="butt" stroke-linejoin="round" opacity="{F(0.2+0.8*(k+1)/nseg)}"/>')
    hx,hy=pts[s-1] if s>0 else pts[-1]
    out.append(f'<circle cx="{F(hx)}" cy="{F(hy)}" r="{F(dot)}" fill="{col}"/>')
    return "".join(out)
def one(x,col,sw=9): return f'<polyline points="{F(x+4)},20 {F(x+20)},2 {F(x+20)},100" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
def times(x,col,cy=58,h=16,sw=9):
    c=x+22; return f'<polyline points="{F(c-h)},{F(cy-h)} {F(c+h)},{F(cy+h)}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/><polyline points="{F(c-h)},{F(cy+h)} {F(c+h)},{F(cy-h)}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="round"/>'
from pathlib import Path

PAST = ["rgb(255,202,196)", "rgb(246,213,167)", "rgb(184,233,198)", "rgb(163,233,241)", "rgb(189,221,255)", "rgb(231,207,255)"]


def fills(x0, cols, rx=27, ry=46, cy=51, inset=4.5):
    return "".join(f'<ellipse cx="{F(x0 + rx * (2 * k + 1))}" cy="{cy}" rx="{F(rx - inset)}" ry="{F(ry - inset)}" fill="{c}"/>'
                   for k, c in enumerate(cols))


def wordmark_body(col, sw=8):
    s, x = [], 0
    for side in (0, 1):
        s.append(one(x, col)); x += 30 + 14
        s.append(fills(x, PAST[3 * side:3 * side + 3]) + trail(triple_path(x), col, sw)); x += 6 * 27
        if side == 0:
            x += 26; s.append(times(x, col)); x += 44 + 26
    return "".join(s), x


def wordmark_svg(col, height=None, extra=""):
    body, W = wordmark_body(col)
    size = f' height="{height}" width="{F(height * (W + 24) / 124)}"' if height else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -12 {F(W + 24)} 124"{size}{extra} role="img" aria-label="1000×1000">{body}</svg>'


def mark_svg(col, style=""):
    w = 6 * 27 + 24
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -{F((w - 124) / 2 + 12)} {w} {w}">{style}'
            f'{fills(0, PAST[:3])}{trail(triple_path(0), col, 9)}</svg>')


if __name__ == "__main__":
    site = Path(__file__).resolve().parents[1] / "site"
    (site / "logo.svg").write_text(wordmark_svg("#16150f") + "\n")
    dark = ("<style>.s{stroke:#16150f;fill:none}.d{fill:#16150f}"
            "@media (prefers-color-scheme:dark){.s{stroke:#f2f1ec}.d{fill:#f2f1ec}}</style>")
    fav = (mark_svg("CURRENT", dark).replace('fill="none" stroke="CURRENT"', 'class="s"')
           .replace('fill="CURRENT"', 'class="d"'))
    (site / "favicon.svg").write_text(fav + "\n")
    print(wordmark_svg("currentColor", 30, ' class="logo" aria-hidden="true" focusable="false"').replace(' role="img" aria-label="1000×1000"', ""))
    pass
