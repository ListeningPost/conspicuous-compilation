#!/usr/bin/env python3
"""Assemble the Rust-only 'Conspicuous Compilation' paper (three methods) as HTML,
then render to PDF with headless Chrome."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIG = REPO / "experiments" / "decompile-cost" / "results" / "figures"
OUT = REPO / "docs" / "conspicuous-compilation-rust.html"


def svg(name: str) -> str:
    return (FIG / name).read_text()


CSS = """
  @page { size: letter; margin: 0.75in 0.7in; }
  :root{ --ink:#111317; --muted:#444b54; --faint:#6b7480; --rule:#c9ccd2;
    --accent:#0E6B4F; --amber:#8C4E08; --codebg:#f4f2ee; --paper:#ffffff; }
  *{ box-sizing:border-box; }
  html{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  body{ font-family:"Liberation Serif","Times New Roman",Georgia,serif;
    color:var(--ink); background:var(--paper); font-size:9.6pt; line-height:1.34; margin:0; }
  .masthead{ text-align:center; border-bottom:1.5pt solid var(--ink); padding-bottom:7pt; margin-bottom:11pt; }
  .venue{ font-family:"Liberation Sans",Arial,sans-serif; font-size:7.3pt;
    letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:700; }
  h1.title{ font-size:19pt; line-height:1.14; margin:7pt 0 3pt; font-weight:700; letter-spacing:-.01em; }
  .subtitle{ font-size:11pt; font-style:italic; color:var(--muted); margin:0 0 9pt; }
  .authors{ font-size:10pt; margin:5pt 0 1pt; }
  .affil{ font-family:"Liberation Sans",Arial,sans-serif; font-size:8pt; color:var(--faint); }
  .absbox{ margin:10pt auto 2pt; max-width:92%; }
  .absbox h3, .kw h3{ font-family:"Liberation Sans",Arial,sans-serif; font-size:8pt;
    letter-spacing:.12em; text-transform:uppercase; color:var(--faint); margin:0 0 3pt; text-align:center; }
  .absbox p{ font-size:9.2pt; text-align:left; margin:0; }
  .kw{ max-width:92%; margin:6pt auto 0; }
  .kw p{ font-size:8.6pt; color:var(--muted); text-align:center; margin:0; }
  .cols{ column-count:2; column-gap:0.32in; column-rule:0.4pt solid #e6e7ea; margin-top:13pt; }
  h2.sec{ font-family:"Liberation Sans",Arial,sans-serif; font-size:9.6pt; font-weight:700; margin:11pt 0 3pt; break-after:avoid; }
  h3.sub{ font-family:"Liberation Sans",Arial,sans-serif; font-size:8.8pt; font-weight:700;
    font-style:normal; color:var(--muted); margin:7pt 0 2pt; break-after:avoid; }
  p.body{ text-align:left; text-wrap:pretty; margin:0 0 5pt; text-indent:11pt; }
  p.body.first, p.noindent{ text-indent:0; }
  .lead::first-letter{ font-size:200%; line-height:.9; font-weight:700; color:var(--accent); }
  code,.mono{ font-family:"Liberation Mono","Courier New",monospace; font-size:8pt; overflow-wrap:anywhere; }
  .code{ background:var(--codebg); border-left:2.5pt solid var(--accent); padding:5pt 7pt;
    margin:3pt 0 5pt; font-family:"Liberation Mono","Courier New",monospace; font-size:7.2pt;
    line-height:1.35; white-space:pre-wrap; break-inside:avoid; color:#1c1f24; }
  .eqn{ display:block; text-align:center; margin:5pt 0; break-inside:avoid; font-size:9.3pt; }
  .eqn .n{ float:right; color:var(--faint); font-size:7.6pt; }
  .appendix{ break-before: page; page: apx; }
  .apxhead{ column-span:all; font-family:"Liberation Sans",Arial,sans-serif; font-size:8pt;
    letter-spacing:.16em; text-transform:uppercase; color:var(--accent); font-weight:700;
    border-bottom:1pt solid var(--ink); padding-bottom:4pt; margin:0 0 10pt; }
  @page apx { margin: 0.78in 0.7in 0.72in;
    @top-center { content: "Conspicuous Compilation · Appendices";
      font-family:"Liberation Sans",Arial,sans-serif; font-size:7pt; color:#6b7480; letter-spacing:.08em; }
    @bottom-center { content: "Listening Post · LLNV-TR-2026-02 · Preprint";
      font-family:"Liberation Sans",Arial,sans-serif; font-size:7pt; color:#6b7480; } }
  figure{ margin:4pt 0 7pt; break-inside:avoid; }
  figure.wide{ column-span:all; margin:6pt 0 9pt; }
  .svgbox{ border:0.4pt solid var(--rule); background:#fff; padding:5pt; }
  .svgbox svg{ width:100%; height:auto; display:block; }
  .svghalf{ max-width:60%; margin:0 auto; }
  .svgrow{ display:flex; gap:10pt; }
  .svgrow .svgbox{ flex:1; }
  figcaption{ font-family:"Liberation Sans",Arial,sans-serif; font-size:7.4pt; color:var(--faint); margin-top:3pt; text-align:left; }
  figcaption b{ color:var(--muted); }
  table.tbl{ width:100%; border-collapse:collapse; font-size:7.8pt; margin:3pt 0 6pt; break-inside:avoid; }
  table.tbl caption{ caption-side:top; font-family:"Liberation Sans",Arial,sans-serif; font-size:7.4pt; color:var(--faint); text-align:left; margin-bottom:3pt; }
  table.tbl th{ font-family:"Liberation Sans",Arial,sans-serif; font-size:7pt; text-transform:uppercase; letter-spacing:.04em; text-align:left; border-bottom:1pt solid var(--ink); padding:2pt 4pt; }
  table.tbl td{ padding:2pt 4pt; border-bottom:0.4pt solid var(--rule); vertical-align:top; }
  table.tbl td.n{ font-family:"Liberation Mono","Courier New",monospace; text-align:right; }
  table.tbl .hi{ color:var(--accent); font-weight:700; }
  .callout{ background:var(--codebg); border-top:1.5pt solid var(--amber); padding:6pt 8pt; margin:4pt 0 6pt; break-inside:avoid; }
  .callout .big{ font-size:14pt; font-weight:700; color:var(--accent); }
  .refs{ font-size:7.6pt; line-height:1.3; }
  .refs ol{ margin:0; padding-left:14pt; }
  .refs li{ margin-bottom:2.5pt; text-align:left; overflow-wrap:anywhere; }
  sup{ font-size:.7em; }
"""

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Conspicuous Compilation</title><style>{CSS}</style></head>
<body>
<div class="masthead">
  <div class="venue">Listening Post &middot; Technical Report LLNV-TR-2026-02 &middot; Preprint</div>
  <h1 class="title">Conspicuous Compilation: Raising the Wall-Clock Cost<br>of Automated Reverse Engineering</h1>
  <div class="subtitle">Three cooperating methods, their attacker cost and their defender cost, measured in Rust</div>
  <div class="authors"><b>William Spicer Berry</b><sup>1</sup> &nbsp;&middot;&nbsp; Seth Steele<sup>1</sup> &nbsp;&middot;&nbsp; Daniel Steele<sup>1</sup></div>
  <div class="affil">1 Listening Post, Inc. &nbsp;&middot;&nbsp; {{wberry, ssteele, dsteele}}@listeningpost.ai</div>
  <div class="affil">Preprint v1 &middot; October 26, 2026</div>
</div>

<div class="absbox"><h3>Abstract</h3>
<p>Automated, agent-driven reverse engineering has wreaked havoc on the industry, taking away
whatever privacy a shipped binary used to have. We study <i>conspicuous compilation</i>: emitting a
behaviourally identical but deliberately analysis-hostile binary, one made hard to understand for
agents and humans alike. Our goal was to raise the wall-clock time an automated decompiler must spend
to understand a compiled program. We combine three methods: control-flow flattening, opaque-predicate
and mixed-boolean-arithmetic (MBA) hardening, and runtime-selected diverse variants. We measure each
alone and together across sixteen Rust functions, confirm with an XOR fingerprint that every build
computes the same result, and run the statistics only on runs that pass that check. In our measurements
decompile cost rose to several hundred times the plain build. We write as industry professionals working
with artificial intelligence, approaching this as a practical problem rather than from a dedicated
research program. We are optimistic that compilation obfuscation like this can
help against agents, but more research, innovation, and attention is needed before it is usable in
production systems.</p></div>
<div class="kw"><h3>Keywords</h3><p>software protection &middot; control-flow flattening &middot;
opaque predicates &middot; mixed boolean arithmetic &middot; runtime diversity &middot; decompilation cost</p></div>

<div class="cols">

<h2 class="sec">1&nbsp;&nbsp;The goal, and the term</h2>
<p class="body first lead">Reverse engineering has always been possible; what changed is its
price, because decompilers driven by language-model agents make scalable, automated analysis
cheap. We respond with a compiler that deliberately inflates the cost of automated analysis while
preserving behaviour.</p>
<p class="body">We call it <b>conspicuous compilation</b> because the binary itself is what gets
obfuscated, and obviously so: the source stays readable and the semantics are unchanged, and only the
binary is made expensive to read. The question we ask is whether, done this way, we can make a binary
meaningfully more expensive to decompile with a tool like Ghidra.</p>

<h2 class="sec">2&nbsp;&nbsp;The three methods</h2>
<p class="body first"><b>Method A, control-flow flattening.</b> Each function becomes a dispatcher
loop whose state variable carries execution order [1, 7, 8], surrounded by <code>J</code> bogus states
that never execute (Figure&nbsp;1).</p>
<p class="body"><b>Method B, opaque predicates and MBA.</b> Every transition routes through an
always-true opaque predicate [2] (<code>7a&sup2;&minus;1 &ne; b&sup2;</code>) and the state constants are
mixed-boolean-arithmetic masked [5], both behind an optimizer barrier, so the compiler cannot prune the
dead edges. We cite prior work using methods similar to Method&nbsp;B that we found after independently
reaching the same ground through agent-driven mathematical exploration. We cite it because it is fair to
assume their work is in the training data that led us to our result, and we thank them for it.</p>
<p class="body"><b>Method C, runtime-selected diverse variants.</b> This one is the simplest. We emit
<code>K</code> independent, shuffled copies of the function and use a hash of the current timestamp to
pick which one runs on each call.</p>
<p class="body">The methods cooperate rather than stack independently: flattening alone is deleted
by the optimizer, and diverse variants only stay distinct once hardened, so method&nbsp;B is what
makes methods&nbsp;A and&nbsp;C survive compilation (Figure&nbsp;3). Flattening and opaque predicates
have been combined before at the IR level [4]; our contribution is the controlled measurement of how
they compose and what each costs.</p>

<figure class="wide"><div class="svgbox">{svg("fig_flatten.svg")}</div>
<figcaption><b>Figure 1.</b> Method A. Flattening turns a linear control-flow graph (left) into a
dispatcher star (right); green nodes are real segments, tan dashed nodes are bogus states. The dial
<code>jumps = J</code> sets how many.</figcaption></figure>

<figure class="wide"><div class="svgbox">{svg("fig_asm.svg")}</div>
<figcaption><b>Figure 2.</b> The same function, disassembled. Left: the plain build is a readable loop
in 63 instructions. Right: methods A and B produce 3,890 instructions in which the loop has dissolved
into a dispatcher over MBA-masked state guarded by the opaque predicate, computing the identical
result.</figcaption></figure>

<figure class="wide"><div class="svgbox">{svg("fig_mechanism.svg")}</div>
<figcaption><b>Figure 3.</b> Why they cooperate. Method A alone is pruned by the optimizer; method B
alone guards only the real path; together the bogus states survive and the graph grows with the
dial.</figcaption></figure>

<figure class="wide"><div class="svgbox">{svg("fig_methodc.svg")}</div>
<figcaption><b>Figure 4.</b> Method C. A wall-clock reading is hashed to an index
<code>e = H(t) mod K</code> that indexes a table of K differently-flattened bodies and runs one of
them; all K compute the identical result, and e changes from call to call, so which body runs is not
statically fixed. The K bodies differ in their constants and also in size and layout: distinct bogus-state counts,
dead-edge wiring, and arm order.</figcaption></figure>

<h2 class="sec">3&nbsp;&nbsp;Experimental design</h2>
<p class="body first">The study is done in Rust, whose optimizer keeps the annotated functions as
standalone symbols, giving a clean same-function baseline in which the plain and obfuscated builds
differ only by the transformation. Each condition builds the same sixteen small functions,
each with a different shape of control flow. Every function returns a number, and the build folds all
sixteen into one fingerprint. That fingerprint comes out the same for the plain build and for every
obfuscated build, so each obfuscated binary computes exactly the same answers as the plain one. The
attacker we model points an automated
decompiler at the binary; in the limiting case a language-model agent is instructed to &ldquo;load the
binary in Ghidra, decompile every function, and summarise what each one does.&rdquo; To measure that cost
deterministically and reproducibly, we remove
the agent and drive Ghidra&nbsp;12.1.4&rsquo;s [6] headless decompiler directly, calling it on each corpus
function ten times and recording the median wall-clock; an agent&rsquo;s own reasoning time sits on top of
this floor. Defender cost is runtime nanoseconds per call. The machine the results were gathered on was
pinned to performance mode and on AC power. All compilation and measurement ran on one
machine: an AMD Ryzen&nbsp;7 7840HS (8 cores / 16 threads, up to 5.14&nbsp;GHz, 16&nbsp;MiB L3), 44&nbsp;GB
RAM, Ubuntu&nbsp;24.04.5 (Linux&nbsp;7.0.0), with rustc&nbsp;1.94.1 and Ghidra&nbsp;12.1.4 on OpenJDK&nbsp;21.</p>

<h2 class="sec">4&nbsp;&nbsp;Attacker cost: decompile wall-clock</h2>
<p class="body first">Three complementary sweeps all raise decompile time steeply. Depth cranks one
function's dial; breadth increases how many functions are obfuscated; variants increases how many
diverse bodies each function carries. Method&nbsp;A alone adds nothing (its bogus states are pruned,
binary size identical to plain); method&nbsp;B alone roughly doubles cost; combined they are
super-additive, 52&times; where independence predicts 2.0&times;. The variants sweep keeps methods&nbsp;A
and&nbsp;B on but pinned to their floor (<code>jumps=8, mba_depth=1</code>) and turns only <code>K</code>,
so its 704&times; at <code>K=64</code> is the cost of all three methods together with A and B held
minimal&mdash;not of method&nbsp;C in isolation.</p>

<figure class="wide"><div class="svgbox">{svg("fig_attacktime.svg")}</div>
<figcaption><b>Figure 5.</b> Depth sweep. Decompile wall-clock for the corpus rises from 61&nbsp;ms
(plain) to 20&nbsp;s (384&times;) as the bogus-branch dial is turned up, for identical
behaviour.</figcaption></figure>

<figure class="wide"><div class="svgrow"><div class="svgbox">{svg("fig_variants.svg")}</div><div class="svgbox">{svg("fig_breadth.svg")}</div></div>
<figcaption><b>Figure 6 (left).</b> Variants: decompile cost grows with <code>K</code> diverse bodies,
to 704&times; at <code>K=64</code>. &nbsp;<b>Figure 7 (right).</b> Breadth: cost grows linearly with the
number of obfuscated functions, about 0.15&nbsp;s per added function.</figcaption></figure>

<table class="tbl"><caption>Table 1. Attacker decompile cost vs plain, three sweeps. Correctness gate held for every row.</caption>
<tr><th>Sweep</th><th>Knob</th><th>Decompile cost</th></tr>
<tr><td>Depth (jumps)</td><td class="n">8&ndash;256</td><td class="n hi">6.3&times; &rarr; 384&times;</td></tr>
<tr><td>Variants (K)</td><td class="n">1&ndash;64</td><td class="n hi">4.6&times; &rarr; 704&times;</td></tr>
<tr><td>Breadth (funcs)</td><td class="n">1&ndash;64</td><td class="n">linear, ~0.15 s / func</td></tr>
</table>

<h2 class="sec">5&nbsp;&nbsp;Defender cost: runtime</h2>
<p class="body first">Runtime is median added nanoseconds per call versus plain, robust to one
microsecond-scale function that would dominate a raw average. Methods&nbsp;A and&nbsp;B add only a
few nanoseconds per call, two orders of magnitude below method&nbsp;C, but they are not quite flat or
free. Method&nbsp;A alone measures zero because the optimizer deletes the flattening; once method&nbsp;B
keeps it from being optimized away, the real path runs through the surviving dispatcher, so A+B rises
from about 2 to 5&nbsp;ns across the dial. Bogus code still never executes; the cost is the few extra
operations the real path now carries. Method&nbsp;C dominates defender cost, because it does work on
every call: a wall-clock read plus an unpredictable dispatch among <code>K</code> bodies.</p>

<figure class="wide"><div class="svgbox">{svg("fig_runtime.svg")}</div>
<figcaption><b>Figure 8.</b> Runtime by method and combination, as added ns/call vs plain. The horizontal
axis is an ordinal <i>level</i> (1&ndash;5), not a calibrated measure of complexity: at each level every
method is turned to the next notch of its own knob, which lets the curves share one axis even though a
notch is not equivalent across methods. Level sets method&nbsp;A&rsquo;s <code>jumps</code> =
8/16/32/64/128, method&nbsp;B&rsquo;s <code>mba_depth</code> = 1/2/3/4/5, and method&nbsp;C&rsquo;s
<code>variants</code> = 2/3/4/6/8; a configuration leaves the knobs it does not use at their floor. Read
each curve for its own trend, not as a method-to-method comparison at a fixed level. Everything without
method&nbsp;C clusters near zero; everything with it sits at +25 to +42&nbsp;ns.</figcaption></figure>

<table class="tbl"><caption>Table 2. Added ns/call at the hardest level tested. Median over the corpus.</caption>
<tr><th>Configuration</th><th>Added ns/call</th></tr>
<tr><td>Method A (flatten)</td><td class="n">~0</td></tr>
<tr><td>Method B (harden)</td><td class="n">+2.5</td></tr>
<tr><td>Methods A+B</td><td class="n">+5</td></tr>
<tr><td>Method C (variants)</td><td class="n hi">+40</td></tr>
<tr><td>All three</td><td class="n hi">+40.5</td></tr>
</table>

<div class="callout"><div class="big">Attacker pays on three knobs; defender mostly on one</div>
<span style="font-size:8pt;color:var(--muted)">Attacker decompile cost scales with every knob;
defender runtime cost is dominated by method&nbsp;C, with methods A and B adding only a few ns that
grows slightly with their dial. Crank the static methods hard for a few nanoseconds; add runtime
diversity only as far as the per-call cost allows.</span></div>

<h2 class="sec">6&nbsp;&nbsp;Threat model and limitations</h2>
<p class="body first">We model a <b>static, automated</b> attacker: a decompiler, possibly
agent-driven. We did not consider any other avenue of attack. A <b>dynamic</b> attacker who runs the
binary under a debugger, for instance, sees the one real path directly, and method&nbsp;C's diversity
resists trace-diffing but not a debugger. This study is simply a measure of economic expense against a
named tool in a specific category [3], and we make no guarantee that agents won't find ways around it
that we did not foresee. We did try to break it ourselves a bit before publishing and did not turn up
anything clever enough to mention. The super-linear growth is an empirical fit, not a proved bound.</p>
<p class="body">We prove no bound on recovery; future agents or decompilers may learn to undo these
transforms, which we do not pursue here. Our question was only whether cheap, behaviour-preserving
transforms make common automated analysis (an LLM agent or a stock Ghidra pass) measurably
slower.</p>

<h2 class="sec">7&nbsp;&nbsp;What we hope is true</h2>
<p class="body first">This section is conjecture, and each claim below needs empirical validation in
further review. The scenario is
server-side software under a modern continuous-integration pipeline with agent-driven updates, where
every build is freshly and differently obfuscated. In that regime, analysing any one build may become
economically silly, for three reasons.</p>
<p class="body"><b>One: a single decompile is already expensive.</b> On our small corpus a best-in-class
automated decompiler already spends tens of seconds per build at a moderate dial, and the breadth result
shows that cost grows linearly with the number of obfuscated functions, so a real codebase would scale
accordingly. If analysing one build costs hours and a new build ships daily, the analysis never catches
its target.</p>
<p class="body"><b>Two: complementary methods may compound.</b> Flattening, hardening and diversity are
not the only transformations possible; we expect further, independent methods to emerge that raise the
same cost, potentially multiplicatively, as hardening already multiplies flattening here. The curve we
measure is super-linear in the dial; what we hope to reach, with further thought, is a transformation
whose cost of decompilation grows <i>exponentially</i> in the dial while the binary&rsquo;s runtime stays flat.</p>
<p class="body"><b>Three: even a working exploit may not fire.</b> Method&nbsp;C selects one of
<code>K</code> variant bodies per call from a wall-clock hash. We measured this selection to be uniform
over the <code>K</code> bodies: at <code>K=8</code> over a million calls each body received within half a
percent of its <code>1/8</code> share, a chi-square goodness-of-fit consistent with uniform at
<code>p=0.05</code>. So which variant&rsquo;s code executes on a given request is not predictable. An exploit
whose reliability depends on a specific variant&rsquo;s code layout would therefore be reached only when
that variant is selected, roughly <code>1/K</code> of the time, and so would not fire deterministically
against a remote target. And by the time such an exploit is developed, a moving-target pipeline has
recompiled the binary some number of times with fresh wirings, leaving a build-specific exploit stale.
We are explicit that this argues only about layout-dependent exploitation: a bug in the shared logic or
in input handling runs regardless of variant, and we have not built an exploit to test any of this. These
claims should be validated empirically in further review.</p>

<h2 class="sec">8&nbsp;&nbsp;Conclusion and reproducibility</h2>
<p class="body first">Conspicuous compilation, with our simple and rather naive methods, raises
automated-decompilation cost by up to nearly three orders of magnitude for behaviour that is
byte-for-byte identical, and the cost structure is
clean: methods&nbsp;A and&nbsp;B buy analysis-hostility for only a few nanoseconds per call, while
method&nbsp;C trades a larger, scaling runtime cost for runtime non-determinism, which we validate directly: its per-call
selector is empirically uniform over the <code>K</code> bodies (at <code>K=8</code> over 10<sup>6</sup>
calls each body lands within half a percent of <code>1/K</code>, a chi-square consistent with uniform),
and the opaque-predicate and MBA identities are proved and numerically checked (Appendix&nbsp;B). All code,
seeds, pinned tool versions and the
exact analysed binaries (with SHA-256) are in <code>experiments/</code> (decompile-cost,
breadth-cost, variants-cost and runtime-cost), each with a build/run/aggregate pipeline and a
reasoning FAQ, so every number regenerates from a single command
(<code>experiments/rerun_experiments.sh</code>) at <code>github.com/ListeningPost/conspicuous-compilation</code>.</p>

<h3 class="sub">8.1&nbsp;&nbsp;What this does not buy, and the defense it implies</h3>
<p class="body first">The numbers above measure the cost to today&rsquo;s decompilers run naively: load,
decompile, summarise. They do not stop a reasoning agent that defeats the transforms structurally.
It is possible that these specific methods, in the configuration we provide, can be learned by the
attacker, whether an agent or an agent swarm, and undone with new methodology. The goal of further
research should be to find methods that combine with these, or supersede them, and that hold even
against the best agents or swarms.</p>
<p class="body">We strongly invite every reader, after enough time has passed to forget the approaches
here, to go create a completely novel way to confuse and confound agents reasoning over binaries. It is
going to take a village for this one.</p>

</div>
<div class="cols appendix">
<div class="apxhead">Appendices</div>
<h2 class="sec">Appendix A&nbsp;&nbsp;The function corpus</h2>
<p class="body first">The corpus is sixteen pure functions, each over an eight-word scratch buffer and
kept out of the inliner so the decompiler must recover it individually. Two representative members
are shown; the full source accompanies the artifact.</p>
<div class="code">pub extern "C" fn even_fib_sum(buf: &amp;mut [u64; 8], _n: u64) -&gt; u64 {{
    buf[0] = 1; buf[1] = 2; buf[2] = 0;
    while buf[0] &lt;= 4_000_000 {{
        if (buf[0] &amp; 1) == 0 {{ buf[2] = buf[2].wrapping_add(buf[0]); }}
        let t = buf[0].wrapping_add(buf[1]);
        buf[0] = buf[1]; buf[1] = t;
    }}
    buf[2]
}}</div>
<div class="code">pub extern "C" fn hash_probe(buf: &amp;mut [u64; 8], n: u64) -&gt; u64 {{
    let mut h = 1469598103934665603u64 ^ n;
    for i in 0..8 {{
        h ^= buf[i];
        h = h.wrapping_mul(1099511628211);
        h ^= h &gt;&gt; 23;
    }}
    h
}}</div>
<p class="body noindent">Obfuscation is one attribute macro: a function is protected by annotating it,
and four knobs select the methods and their strength.</p>
<div class="code">#[llnv_obfuscate(flatten=1, harden=1, jumps=64, mba_depth=2, variants=4)]
pub extern "C" fn even_fib_sum(buf: &amp;mut [u64; 8], _n: u64) -&gt; u64 {{ /* ... */ }}</div>
<p class="body noindent"><b>Notes for the reader.</b> <code>flatten</code> toggles method A,
<code>harden</code> method B, and <code>variants = K</code> method C; <code>jumps</code> sets the
bogus-state count and <code>mba_depth</code> the masking depth. Functions are declared
<code>#[no_mangle] extern "C"</code> so Rust keeps each as a standalone symbol. Every build evaluates
an XOR-fold of all sixteen outputs, and that gate value is byte-identical across every condition, so a
differing result aborts the build and each reported number is the cost of representing the same
computation. Builds are reproducible with a pinned seed (<code>LLNV_SEED=7</code>); unset, the seed is
drawn from the wall clock so each rebuild is wired differently.</p>

<h2 class="sec">Appendix B&nbsp;&nbsp;Mathematical formulation</h2>
<p class="body first">Each step below is validated against the implementation; the two identities are
proved and numerically checked. The Rust dispatcher keeps the real body as a single segment, so, unlike a multi-segment source flattener, there is
no cross-segment def/use condition, and the
corresponding equations are omitted deliberately.</p>
<p class="body noindent"><b>Method A (flattening).</b> States get distinct constants from a high band,
and the dial fixes the bogus count, so the dispatcher is linear in it:</p>
<div class="eqn">&sigma; : {{entry, real}} &cup; B &rarr; [2<sup>20</sup>, 2<sup>21</sup>), injective <span class="n">(B1)</span></div>
<div class="eqn">|B| = J, &nbsp; M = |B| + 2 = J + 2 = &Theta;(J) <span class="n">(B2)</span></div>
<p class="body noindent"><b>Method B (hardening).</b> Each transition is guarded by an always-true opaque
predicate, and state constants are MBA-masked by an always-zero term:</p>
<div class="eqn">&Omega;(a,b) = [ 7a<sup>2</sup> &minus; 1 &ne; b<sup>2</sup> ] = true &nbsp; for all a,b &isin; &#8484; <span class="n">(B3)</span></div>
<div class="eqn">&mu;(m) = m(m+1) mod 2 = 0, &nbsp; v &#8614; v &oplus; &mu;(m) = v <span class="n">(B4)</span></div>
<div class="eqn">st &larr; &Omega;(a,b) ? &sigma;(real) : &beta;, &nbsp; &beta; &isin; B <span class="n">(B5)</span></div>
<p class="body noindent"><b>Proof of (B3).</b> If 7a<sup>2</sup>&minus;1 = b<sup>2</sup> then
b<sup>2</sup> &equiv; &minus;1 &equiv; 6 (mod 7); the quadratic residues mod 7 are {{0, 1, 2, 4}}, and 6 is
not among them, so no such b exists. Operands are masked to 30 bits, so
7a<sup>2</sup>&minus;1 &le; 7(2<sup>30</sup>&minus;1)<sup>2</sup> &lt; 2<sup>64</sup> stays exact.
<b>(B4)</b> holds because m(m+1) is a product of consecutive integers and hence even, so the mask is
identically zero; it still resists constant propagation because the operand passes an optimizer barrier.
A brute-force check finds no counterexample to either identity up to a&nbsp;=&nbsp;3&times;10<sup>5</sup>
and m&nbsp;=&nbsp;10<sup>6</sup>.</p>
<p class="body noindent"><b>Method C (variants).</b> One of K bodies is selected per call by the
MurmurHash3 finalizer H over the wall-clock time t:</p>
<div class="eqn">e = H(t) mod K <span class="n">(B6)</span></div>
<p class="body noindent">Empirically e is uniform over {{0, &hellip;, K&minus;1}}:
at K&nbsp;=&nbsp;8, over 10<sup>6</sup> calls each body received 12.5% &plusmn; 0.1%, a chi-square
goodness-of-fit consistent with uniform at p&nbsp;=&nbsp;0.05 (median chi-square well below the 14.07
critical value for 7 d.o.f.). Consecutive calls repeat at a rate near the 1/K baseline, but that serial
rate is a live-timing quantity sensitive to clock granularity and CPU state, so the reproducible
selector statistic is the uniform body distribution (harness and artifact:
<code>experiments/variants-cost/selector_uniformity.rs</code>). Each of the K bodies is drawn independently from the
seeded generator with its own bogus-state count (around the dial), a randomized dead-edge permutation,
and a shuffled arm order, so they are pairwise non-isomorphic control-flow graphs; for example at
<code>jumps=12</code> four variants carried 9, 15, 14 and 23 bogus states at distinct layout positions.</p>

<h2 class="sec">Acknowledgments and disclosure</h2>
<p class="body first"><b>AI assistance.</b> This work was produced with substantial AI assistance: a
human-directed AI coding agent implemented the <code>#[llnv_obfuscate]</code> toolchain, the
measurement harnesses, and a draft of this manuscript, under the authors&rsquo; direction. The authors
reviewed the methods and results and take responsibility for the claims. We regard building defenses
against agent-driven reverse engineering with agent assistance, in the open, as appropriate to the
problem. We do not take our own numbers on faith, and we ask that you not either: the complete
pipeline, pinned tool versions (rustc&nbsp;1.94.1, Ghidra&nbsp;12.1.4), the fixed seed
(<code>LLNV_SEED=7</code>), and every analysed binary with its SHA-256 are published so that any
reader, human or agent, can reproduce every figure independently on their own machine.</p>
<p class="body"><b>Code and data availability.</b> All source, the build/run/aggregate pipelines, the raw
Ghidra logs, and the aggregated results are available at <code>github.com/ListeningPost/conspicuous-compilation</code>
under Apache-2.0. A single command, <code>experiments/rerun_experiments.sh</code>, regenerates every
figure from clean builds, each run gated so a decompile that does not complete is never counted.</p>

<div class="refs">
<h2 class="sec">References</h2>
<ol>
<li>C. Collberg, C. Thomborson, and D. Low. A Taxonomy of Obfuscating Transformations. Tech. Rep. 148, Univ. of Auckland, 1997.</li>
<li>C. Collberg, C. Thomborson, and D. Low. Manufacturing Cheap, Resilient, and Stealthy Opaque Constructs. In <i>POPL</i>, pp. 184&ndash;196, 1998.</li>
<li>B. Barak et&nbsp;al. On the (Im)possibility of Obfuscating Programs. In <i>CRYPTO</i>, LNCS 2139, pp. 1&ndash;18, 2001.</li>
<li>P. Junod, J. Rinaldini, J. Wehrli, and J. Michielin. Obfuscator-LLVM &mdash; Software Protection for the Masses. In <i>IEEE/ACM SPRO</i>, pp. 3&ndash;9, 2015.</li>
<li>Y. Zhou, A. Main, Y. X. Gu, and H. Johnson. Information Hiding in Software with Mixed Boolean-Arithmetic Transforms. In <i>WISA</i>, LNCS 4867, pp. 61&ndash;75, 2007.</li>
<li>National Security Agency. Ghidra Software Reverse Engineering Framework. https://ghidra-sre.org and github.com/NationalSecurityAgency/ghidra. (Version 12.1.4, as used here.)</li>
<li>C. Wang, J. Hill, J. Knight, and J. Davidson. Software Tamper Resistance: Obstructing Static Analysis of Programs. Tech. Rep. CS-2000-12, Univ. of Virginia, 2000.</li>
<li>T. L&aacute;szl&oacute; and &Aacute;. Kiss. Obfuscating C++ Programs via Control Flow Flattening. <i>Annales Univ. Sci. Budapest., Sect. Comp.</i>, 30:3&ndash;19, 2009.</li>
</ol>
</div>

</div>
</body></html>
"""

OUT.write_text(HTML)
print("wrote", OUT, f"({len(HTML):,} bytes)")
