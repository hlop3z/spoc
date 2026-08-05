package ensure

import (
	"fmt"
	"io"
	"os/exec"
	"runtime"
	"strings"
)

// Toolchain is a language toolchain this repository builds with.
//
// Unlike a [Tool], a toolchain is never installed automatically. A compiler is
// the developer's environment, not something a workshop script should reshape
// behind their back — so this half of the package only ever reports, and hands
// back the command to run if the answer is "missing".
type Toolchain struct {
	// Label is how the toolchain is named in the report.
	Label string
	// Names are candidate executables on PATH, first match wins.
	Names []string
	// VersionArgs asks the tool for its version. Not always "--version": `go`
	// answers to `go version` and fails on the flag.
	VersionArgs []string
	// Purpose is what this repository needs it for, shown when it is missing.
	Purpose string
	// Required means `task check` cannot pass without it.
	Required bool
	// Install maps GOOS to install commands, most convenient first.
	Install map[string][]string
	// Hint is the canonical install page, for platforms Install misses.
	Hint string
}

// Toolchains is the set a developer needs before starting work here.
//
// Required entries are the ones `task check` already depends on; their absence
// is a broken build waiting to happen. The rest are declared so their absence is
// known up front rather than discovered halfway through a task that needs them.
var Toolchains = []Toolchain{
	{
		Label:       "uv",
		Names:       []string{"uv"},
		VersionArgs: []string{"--version"},
		Purpose:     "every Python task — sync, test, lint, type, docs",
		Required:    true,
		Install: map[string][]string{
			"windows": {
				"winget install -e --id astral-sh.uv",
				`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`,
			},
			"darwin": {"brew install uv", "curl -LsSf https://astral.sh/uv/install.sh | sh"},
			"linux":  {"curl -LsSf https://astral.sh/uv/install.sh | sh"},
		},
		Hint: "https://docs.astral.sh/uv/getting-started/installation/",
	},
	{
		Label:       "python",
		Names:       []string{"python", "python3"},
		VersionArgs: []string{"--version"},
		Purpose:     "the runtime SPOC targets (3.13+)",
		Required:    true,
		Install: map[string][]string{
			"windows": {"uv python install 3.13"},
			"darwin":  {"uv python install 3.13"},
			"linux":   {"uv python install 3.13"},
		},
		Hint: "uv installs and pins interpreters itself — prefer it over a system Python",
	},
	{
		Label:       "go",
		Names:       []string{"go"},
		VersionArgs: []string{"version"},
		Purpose:     "the workshop binaries — task lint:go, build:go",
		Required:    true,
		Install: map[string][]string{
			"windows": {"winget install -e --id GoLang.Go"},
			"darwin":  {"brew install go"},
			"linux":   {"brew install go"},
		},
		Hint: "https://go.dev/dl/",
	},
	{
		Label:       "cargo",
		Names:       []string{"cargo"},
		VersionArgs: []string{"--version"},
		Purpose:     "the cargo-install fallback in `ensure`, and any future Rust work",
		Install: map[string][]string{
			"windows": {"winget install -e --id Rustlang.Rustup"},
			"darwin":  {"curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"},
			"linux":   {"curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"},
		},
		Hint: "https://rustup.rs",
	},
	{
		Label:       "rustc",
		Names:       []string{"rustc"},
		VersionArgs: []string{"--version"},
		Purpose:     "compiling Rust — cargo drives it but cannot replace it",
		Hint:        "installed by rustup alongside cargo; if only one is missing, run `rustup update`",
	},
}

// Status is what [Doctor] found for one toolchain.
type Status struct {
	Label    string `json:"label"`
	Found    bool   `json:"found"`
	Required bool   `json:"required"`
	Path     string `json:"path,omitempty"`
	Version  string `json:"version,omitempty"`
	Purpose  string `json:"purpose"`

	tool Toolchain
}

// Doctor resolves each toolchain against PATH. It installs nothing and changes
// nothing; the only processes it starts are version queries against binaries
// that already resolved.
func Doctor(chains []Toolchain) []Status {
	out := make([]Status, 0, len(chains))
	for _, tc := range chains {
		st := Status{Label: tc.Label, Required: tc.Required, Purpose: tc.Purpose, tool: tc}
		for _, name := range tc.Names {
			path, err := exec.LookPath(name)
			if err != nil || isStoreStub(path) {
				continue
			}
			st.Found, st.Path, st.Version = true, path, version(path, tc.VersionArgs...)
			break
		}
		out = append(out, st)
	}
	return out
}

// MissingRequired counts the toolchains whose absence breaks `task check`.
func MissingRequired(statuses []Status) int {
	n := 0
	for _, st := range statuses {
		if !st.Found && st.Required {
			n++
		}
	}
	return n
}

// isStoreStub reports whether path is one of Windows' App Execution Aliases.
// Those stubs are named exactly like the real interpreter but open the Microsoft
// Store instead of answering, so they are rejected on sight rather than run —
// executing one would pop a Store window in the middle of a status check.
func isStoreStub(path string) bool {
	return runtime.GOOS == "windows" &&
		strings.Contains(strings.ToLower(path), `\windowsapps\`)
}

// Report writes the human-readable status table and, for anything missing, the
// command that fixes it on this platform.
func Report(w io.Writer, statuses []Status, showPaths bool) {
	width := 0
	for _, st := range statuses {
		if n := len(st.Label); n > width {
			width = n
		}
	}

	fmt.Fprintf(w, "toolchains (%s/%s)\n\n", runtime.GOOS, runtime.GOARCH)

	var missing []Status
	for _, st := range statuses {
		switch {
		case st.Found:
			detail := st.Version
			if detail == "" {
				detail = "(version unavailable)"
			}
			fmt.Fprintf(w, "  %-*s  ok   %s\n", width, st.Label, detail)
			if showPaths {
				fmt.Fprintf(w, "  %-*s       %s\n", width, "", st.Path)
			}
		default:
			missing = append(missing, st)
			fmt.Fprintf(w, "  %-*s  --   not on PATH  (%s)\n", width, st.Label, requirement(st))
		}
	}

	for _, st := range missing {
		fmt.Fprintf(w, "\n%s — %s\n", st.Label, st.Purpose)
		for _, cmd := range st.tool.Install[runtime.GOOS] {
			fmt.Fprintf(w, "    %s\n", cmd)
		}
		if st.tool.Hint != "" {
			fmt.Fprintf(w, "    %s\n", st.tool.Hint)
		}
	}

	required := MissingRequired(statuses)
	fmt.Fprintln(w)
	switch {
	case required > 0:
		fmt.Fprintf(w, "%d required missing — `task check` will not pass\n", required)
	case len(missing) > 0:
		fmt.Fprintf(w, "all required toolchains present; %d optional missing\n", len(missing))
	default:
		fmt.Fprintln(w, "all toolchains present")
	}
}

func requirement(st Status) string {
	if st.Required {
		return "required"
	}
	return "optional"
}
