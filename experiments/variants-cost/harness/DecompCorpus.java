import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.util.*;

// Decompile every corpus function (name starts "fn_") K times and report, per
// function, the median decompile time (ms), body size, AND an explicit decompile
// STATUS. Earlier versions discarded the DecompileResults, so a failed or
// timed-out decompile was timed and recorded as if it were a fast success; a
// 0 ms row was indistinguishable from an instant failure. This version verifies
// every decompile completed and produced a function body, emits OK/FAIL per
// function, names the error on failure, and prints a DCDONE sentinel so a run
// that silently produced nothing (or partial output) is detectable downstream.
//
// Output lines (Ghidra prefixes each with "INFO  DecompCorpus.java> " at runtime):
//   DC <funcname> <OK|FAIL> <median_ms> <min_ms> <max_ms> <body_bytes>
//   DCERR <funcname> <error message>        (only emitted when a decompile failed)
//   DCDONE <ok_count> <total_count>         (sentinel; its absence means the run did not finish)
public class DecompCorpus extends GhidraScript {
    @Override public void run() throws Exception {
        final int K = 10; // median of 10 timed decompiles per function
        final int TIMEOUT = 240; // seconds, per decompile call
        DecompInterface di = new DecompInterface();
        if (!di.openProgram(currentProgram)) {
            println("DCERR <program> openProgram failed: " + di.getLastMessage());
            println("DCDONE 0 0");
            return;
        }
        List<Function> fns = new ArrayList<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true))
            if (f.getName().startsWith("fn_")) fns.add(f);
        Collections.sort(fns, (a, b) -> a.getName().compareTo(b.getName()));

        int ok = 0;
        for (Function f : fns) {
            String err = decompileError(di.decompileFunction(f, TIMEOUT, monitor)); // warm + verify
            long[] xs = new long[K];
            for (int i = 0; i < K && err == null; i++) {
                long t0 = System.nanoTime();
                DecompileResults r = di.decompileFunction(f, TIMEOUT, monitor);
                xs[i] = (System.nanoTime() - t0) / 1000000;
                err = decompileError(r);
            }
            long body = f.getBody().getNumAddresses();
            if (err == null) {
                Arrays.sort(xs);
                long med = (xs[(K-1)/2] + xs[K/2]) / 2;
                println("DC " + f.getName() + " OK " + med + " " + xs[0] + " " + xs[K-1] + " " + body);
                ok++;
            } else {
                println("DCERR " + f.getName() + " " + err);
                println("DC " + f.getName() + " FAIL -1 -1 -1 " + body);
            }
        }
        di.dispose();
        println("DCDONE " + ok + " " + fns.size());
    }

    // Returns null when the decompile genuinely completed with a function body,
    // otherwise a short reason string.
    private static String decompileError(DecompileResults r) {
        if (r == null) return "null results";
        if (!r.decompileCompleted()) {
            String m = r.getErrorMessage();
            return (m == null || m.isEmpty()) ? "decompile did not complete" : m.replace('\n', ' ');
        }
        if (r.getDecompiledFunction() == null) return "no decompiled function body";
        return null;
    }
}
