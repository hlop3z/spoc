// Package ensure makes a mature third-party CLI available without rebuilding it.
//
// The canon's rule is to adopt, never reinvent. Adopting has exactly one cost —
// the tool has to actually be present — and this package pays it, using the
// least invasive installer the platform already offers.
package ensure

import (
	"errors"
	"fmt"
	"io"
	"os/exec"
	"runtime"
	"strings"
)

// Method selects how far ensure is allowed to go to obtain a tool.
type Method string

const (
	// MethodAuto tries every strategy in order of increasing invasiveness.
	MethodAuto Method = "auto"
	// MethodPkg uses only an OS package manager.
	MethodPkg Method = "pkg"
	// MethodCargo uses only cargo.
	MethodCargo Method = "cargo"
)

// Tool describes a third-party CLI and how each platform installs it.
type Tool struct {
	// Name is the executable as it appears on PATH.
	Name string
	// Crate is the crates.io name, when the tool is installable via cargo.
	Crate string
	// PkgInstall maps GOOS to ordered package-manager commands to try.
	PkgInstall map[string][][]string
	// Hint names other install routes for platforms nothing here covers.
	Hint string
}

// Tokei counts lines of code across every language. Mature, widely packaged,
// and explicitly not something to reimplement.
//
// Note it ships NO prebuilt binaries: every GitHub release has zero assets, so
// a download strategy is not available for this tool. Package manager, then
// cargo, is the whole of it.
var Tokei = Tool{
	Name:  "tokei",
	Crate: "tokei",
	PkgInstall: map[string][][]string{
		"windows": {
			{"winget", "install", "-e", "--id", "XAMPPRocky.Tokei"},
			{"scoop", "install", "tokei"},
		},
		"darwin": {
			{"brew", "install", "tokei"},
		},
		"linux": {
			{"brew", "install", "tokei"},
		},
	},
	Hint: "tokei is also packaged for Arch, Nix, and Alpine — check your distro before falling back to cargo",
}

// ErrNotObtained means every permitted strategy failed.
var ErrNotObtained = errors.New("could not obtain tool")

// Result reports where a tool came from.
type Result struct {
	Path     string
	Strategy string
	Version  string
}

// Ensure returns a usable path to the tool, installing it if necessary.
//
// Strategies run from least to most invasive: an existing install, then the OS
// package manager, then cargo. Installing a Rust toolchain is deliberately last
// and opt-in — pulling in a whole compiler to obtain one binary is the heaviest
// possible answer to the question.
func Ensure(t Tool, method Method, allowRustup bool, out io.Writer) (Result, error) {
	if path, err := exec.LookPath(t.Name); err == nil {
		return Result{Path: path, Strategy: "already installed", Version: version(path)}, nil
	}

	var attempted []string

	if method == MethodAuto || method == MethodPkg {
		path, mgr, err := installViaPkg(t, out)
		if err == nil {
			return Result{Path: path, Strategy: mgr, Version: version(path)}, nil
		}
		attempted = append(attempted, "package manager: "+err.Error())
	}

	if method == MethodAuto || method == MethodCargo {
		path, err := installViaCargo(t, allowRustup, out)
		if err == nil {
			return Result{Path: path, Strategy: "cargo install", Version: version(path)}, nil
		}
		attempted = append(attempted, "cargo: "+err.Error())
	}

	msg := fmt.Sprintf("%v %q on %s/%s; tried:\n  - %s",
		ErrNotObtained, t.Name, runtime.GOOS, runtime.GOARCH, strings.Join(attempted, "\n  - "))
	if t.Hint != "" {
		msg += "\n\nhint: " + t.Hint
	}
	return Result{}, errors.New(msg)
}

func installViaPkg(t Tool, out io.Writer) (string, string, error) {
	cmds, ok := t.PkgInstall[runtime.GOOS]
	if !ok || len(cmds) == 0 {
		return "", "", fmt.Errorf("none configured for %s", runtime.GOOS)
	}

	var tried []string
	for _, argv := range cmds {
		mgr := argv[0]
		if _, err := exec.LookPath(mgr); err != nil {
			tried = append(tried, mgr+" (not installed)")
			continue
		}
		fmt.Fprintf(out, "  installing via %s...\n", mgr)
		if err := run(argv, out); err != nil {
			tried = append(tried, fmt.Sprintf("%s (failed: %v)", mgr, err))
			continue
		}
		if path, err := exec.LookPath(t.Name); err == nil {
			return path, mgr, nil
		}
		// Some managers need a fresh shell before the binary resolves.
		tried = append(tried, mgr+" (installed, but not on PATH yet — reopen your shell)")
	}
	return "", "", errors.New(strings.Join(tried, "; "))
}

func installViaCargo(t Tool, allowRustup bool, out io.Writer) (string, error) {
	if t.Crate == "" {
		return "", errors.New("not published on crates.io")
	}

	if _, err := exec.LookPath("cargo"); err != nil {
		if !allowRustup {
			return "", errors.New("cargo not installed; re-run with --allow-rustup to install the Rust toolchain first")
		}
		if err := installRustup(out); err != nil {
			return "", fmt.Errorf("installing rustup: %w", err)
		}
	}

	fmt.Fprintf(out, "  cargo install %s (compiles from source; this is slow)...\n", t.Crate)
	if err := run([]string{"cargo", "install", t.Crate}, out); err != nil {
		return "", err
	}
	path, err := exec.LookPath(t.Name)
	if err != nil {
		return "", errors.New("cargo succeeded but the binary is not on PATH; add ~/.cargo/bin to PATH")
	}
	return path, nil
}

// installRustup pulls in an entire Rust toolchain. It runs only behind an
// explicit flag because it is a large, system-wide change made to obtain a
// single binary — every lighter strategy should be exhausted first.
func installRustup(out io.Writer) error {
	fmt.Fprintln(out, "  installing the Rust toolchain via rustup...")
	switch runtime.GOOS {
	case "windows":
		if _, err := exec.LookPath("winget"); err == nil {
			return run([]string{"winget", "install", "-e", "--id", "Rustlang.Rustup"}, out)
		}
		return errors.New("winget unavailable; install Rust from https://rustup.rs")
	default:
		if _, err := exec.LookPath("sh"); err != nil {
			return errors.New("sh unavailable; install Rust from https://rustup.rs")
		}
		return run([]string{"sh", "-c",
			"curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"}, out)
	}
}

func run(argv []string, out io.Writer) error {
	cmd := exec.Command(argv[0], argv[1:]...)
	cmd.Stdout = out
	cmd.Stderr = out
	return cmd.Run()
}

func version(path string) string {
	b, err := exec.Command(path, "--version").Output()
	if err != nil {
		return ""
	}
	return strings.TrimSpace(string(b))
}
