// Command ensure reports on — and where appropriate obtains — the tools this
// repository is built with.
//
// It exists because the canon forbids reimplementing a tool that already exists
// and works. Adopting has one cost — the tool must actually be installed — and
// this pays it with the least invasive method the platform offers. `doctor`
// covers the other half: the language toolchains, which are reported on but
// never installed automatically.
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"tools/internal/ensure"
)

func main() {
	root := &cobra.Command{
		Use:          "ensure",
		Short:        "Report on and obtain the tools this repository builds with",
		SilenceUsage: true,
	}

	root.AddCommand(tokeiCmd(), doctorCmd())

	if err := root.Execute(); err != nil {
		os.Exit(1)
	}
}

func tokeiCmd() *cobra.Command {
	var (
		method      string
		allowRustup bool
		pathOnly    bool
	)

	cmd := &cobra.Command{
		Use:   "tokei",
		Short: "Count lines of code (github.com/XAMPPRocky/tokei)",
		Long: "Finds an existing install, or obtains tokei using the least invasive method " +
			"this platform offers: an OS package manager first, then cargo. Installing a Rust " +
			"toolchain is opt-in via --allow-rustup.",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return obtain(cmd, ensure.Tokei, method, allowRustup, pathOnly)
		},
	}

	cmd.Flags().StringVar(&method, "method", "auto", "auto, pkg, or cargo")
	cmd.Flags().BoolVar(&allowRustup, "allow-rustup", false, "permit installing the Rust toolchain as a last resort")
	cmd.Flags().BoolVar(&pathOnly, "path", false, "print only the resolved path, for scripting")
	return cmd
}

func doctorCmd() *cobra.Command {
	var (
		asJSON    bool
		showPaths bool
	)

	cmd := &cobra.Command{
		Use:   "doctor",
		Short: "Report which language toolchains are on PATH",
		Long: "Checks uv, python, go, cargo, and rustc without installing or changing anything, " +
			"so a missing toolchain is known before the task that needs it fails. Exits non-zero " +
			"when a toolchain `task check` depends on is missing; optional ones are reported and " +
			"forgiven.",
		Args: cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			statuses := ensure.Doctor(ensure.Toolchains)

			if asJSON {
				enc := json.NewEncoder(cmd.OutOrStdout())
				enc.SetIndent("", "  ")
				if err := enc.Encode(statuses); err != nil {
					return err
				}
			} else {
				ensure.Report(cmd.OutOrStdout(), statuses, showPaths)
			}

			if n := ensure.MissingRequired(statuses); n > 0 {
				return fmt.Errorf("%d required toolchain(s) missing", n)
			}
			return nil
		},
	}

	cmd.Flags().BoolVar(&asJSON, "json", false, "emit the report as JSON, for another tool to consume")
	cmd.Flags().BoolVar(&showPaths, "paths", false, "show the resolved path for each toolchain found")
	return cmd
}

func obtain(cmd *cobra.Command, tool ensure.Tool, method string, allowRustup, pathOnly bool) error {
	// Progress narration goes to stderr so --path stays pipeable.
	progress := cmd.ErrOrStderr()
	if !pathOnly {
		fmt.Fprintf(progress, "ensuring %s...\n", tool.Name)
	}

	res, err := ensure.Ensure(tool, ensure.Method(method), allowRustup, progress)
	if err != nil {
		return err
	}

	if pathOnly {
		fmt.Fprintln(cmd.OutOrStdout(), res.Path)
		return nil
	}

	fmt.Fprintf(cmd.OutOrStdout(), "%s ready (%s)\n  path:    %s\n", tool.Name, res.Strategy, res.Path)
	if res.Version != "" {
		fmt.Fprintf(cmd.OutOrStdout(), "  version: %s\n", res.Version)
	}
	return nil
}
