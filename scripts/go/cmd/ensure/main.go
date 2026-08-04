// Command ensure makes a mature third-party CLI available on this machine.
//
// It exists because the canon forbids reimplementing a tool that already exists
// and works. Adopting has one cost — the tool must actually be installed — and
// this pays it with the least invasive method the platform offers.
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"tools/internal/ensure"
)

func main() {
	var (
		method      string
		allowRustup bool
		pathOnly    bool
	)

	root := &cobra.Command{
		Use:   "ensure",
		Short: "Make a mature third-party CLI available",
		Long: "Finds an existing install, or obtains the tool using the least invasive method " +
			"this platform offers: an OS package manager first, then cargo. Installing a Rust " +
			"toolchain is opt-in via --allow-rustup.",
		SilenceUsage: true,
	}

	root.PersistentFlags().StringVar(&method, "method", "auto", "auto, pkg, or cargo")
	root.PersistentFlags().BoolVar(&allowRustup, "allow-rustup", false, "permit installing the Rust toolchain as a last resort")
	root.PersistentFlags().BoolVar(&pathOnly, "path", false, "print only the resolved path, for scripting")

	root.AddCommand(&cobra.Command{
		Use:   "tokei",
		Short: "Count lines of code (github.com/XAMPPRocky/tokei)",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, _ []string) error {
			return obtain(cmd, ensure.Tokei, method, allowRustup, pathOnly)
		},
	})

	if err := root.Execute(); err != nil {
		os.Exit(1)
	}
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
