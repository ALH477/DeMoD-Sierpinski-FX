{
  description = "DeMoD Sierpinski FX System v2.4 — Argent Metal Edition";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];

      # ── Overlay ────────────────────────────────────────────────────────────
      # Adds pretty-midi to python311Packages (not in upstream nixpkgs).
      #
      # To fill in the real hash, run:
      #   nix-prefetch-url --unpack \
      #     https://files.pythonhosted.org/packages/source/p/pretty_midi/pretty_midi-0.2.10.tar.gz
      # and replace the sha256 value below.
      overlays = [
        (final: prev: {
          python311 = prev.python311.override {
            packageOverrides = pyFinal: pyPrev: {
              pretty-midi = pyPrev.buildPythonPackage rec {
                pname   = "pretty_midi";
                version = "0.2.10";
                format  = "setuptools";

                src = prev.fetchPypi {
                  inherit pname version;
                  # ↓ replace after running nix-prefetch-url above
                  sha256 = "sha256-6m4ZL5QERnToMzNuofQVMY3fKOMgMCrHsQnt/w1FNL0=";
                };

                propagatedBuildInputs = with pyPrev; [
                  numpy
                  mido   # pure-python MIDI I/O, already in nixpkgs
                ];

                # Upstream tests require audio hardware / network fixtures.
                doCheck = false;

                meta = with prev.lib; {
                  description = "Functions and classes for handling MIDI data conveniently";
                  homepage    = "https://github.com/craffel/pretty-midi";
                  license     = licenses.mit;
                  maintainers = [];
                };
              };
            };
          };
          # Propagate override so python311Packages also resolves correctly.
          python311Packages = final.python311.pkgs;
        })
      ];

      # ── Per-system pkgs with overlay applied ───────────────────────────────
      pkgsFor = system: import nixpkgs { inherit system overlays; };

      # ── Shared Python environment ──────────────────────────────────────────
      mkPythonEnv = pkgs: pkgs.python311.withPackages (ps: with ps; [
        rich
        questionary
        pretty-midi   # provided by overlay above
        soundfile
        numpy
      ]);

    in
    {
      # Expose overlay so downstream flakes can consume it.
      overlays.default = builtins.head overlays;

      # ── Packages ───────────────────────────────────────────────────────────
      packages = forAllSystems (system:
        let
          pkgs  = pkgsFor system;
          pyEnv = mkPythonEnv pkgs;
        in
        {
          # Thin launcher — no runtime pip, no double-exec.
          beater = pkgs.writeShellScriptBin "demod-sierpinski-beater" ''
            exec ${pyEnv}/bin/python -c "from demod_sierpinski_beater import main; main()"
          '';

          fx-lv2 = pkgs.stdenv.mkDerivation {
            pname   = "demod-sierpinski-fx";
            version = "2.4";
            src     = ./demod_sierpinski_fx.lv2;
            dontBuild = true;
            installPhase = ''
              runHook preInstall
              mkdir -p $out/lib/lv2
              cp -r . $out/lib/lv2/demod_sierpinski_fx.lv2
              runHook postInstall
            '';
          };

          bundle = pkgs.stdenv.mkDerivation {
            pname   = "demod-sierpinski-fx-bundle";
            version = "2.4";
            src     = ./.;
            dontBuild = true;
            installPhase = ''
              runHook preInstall

              mkdir -p $out/share/demod-sierpinski-fx
              cp -r demod_sierpinski_fx.lv2  $out/share/demod-sierpinski-fx/
              cp demod_sierpinski_fx.dsp      $out/share/demod-sierpinski-fx/
              cp demod_sierpinski_beater.py   $out/share/demod-sierpinski-fx/
              cp pyproject.toml               $out/share/demod-sierpinski-fx/
              cp README.md                    $out/share/demod-sierpinski-fx/

              mkdir -p $out/bin
              cat > $out/bin/demod-sierpinski-beater << EOF
              #!/bin/sh
              exec ${pyEnv}/bin/python \
                $out/share/demod-sierpinski-fx/demod_sierpinski_beater.py "\$@"
              EOF
              chmod +x $out/bin/demod-sierpinski-beater

              runHook postInstall
            '';
          };

          # `nix build` with no attr lands here.
          default = self.packages.${system}.beater;
        }
      );

      # ── Dev shell ──────────────────────────────────────────────────────────
      devShells = forAllSystems (system:
        let
          pkgs  = pkgsFor system;
          pyEnv = mkPythonEnv pkgs;
        in
        {
          default = pkgs.mkShell {
            packages = [
              pyEnv
              pkgs.faust
              pkgs.fluidsynth
              pkgs.lv2
              pkgs.jack2
              pkgs.python311Packages.black
              pkgs.python311Packages.ruff
            ];
            shellHook = ''
              echo "DeMoD Sierpinski Argent Metal Edition v2.4 — dev shell"
              echo "  Run: demod-sierpinski-beater"
            '';
          };
        }
      );

      # ── Apps ───────────────────────────────────────────────────────────────
      apps = forAllSystems (system: {
        default = {
          type    = "app";
          program = "${self.packages.${system}.beater}/bin/demod-sierpinski-beater";
        };
      });

      # ── NixOS module ───────────────────────────────────────────────────────
      # Host config must include self.overlays.default in nixpkgs.overlays
      # so that pkgs here has pretty-midi available. Example:
      #
      #   nixpkgs.overlays = [ demod-sierpinski.overlays.default ];
      #   imports = [ demod-sierpinski.nixosModules.default ];
      #
      nixosModules.default = { lib, pkgs, ... }:
        let
          pyEnv = mkPythonEnv pkgs;
        in
        {
          environment.systemPackages = [
            pyEnv
            (pkgs.writeShellScriptBin "demod-sierpinski-beater" ''
              exec ${pyEnv}/bin/python -c \
                "from demod_sierpinski_beater import main; main()"
            '')
            (pkgs.stdenv.mkDerivation {
              pname   = "demod-sierpinski-fx";
              version = "2.4";
              src     = ./demod_sierpinski_fx.lv2;
              dontBuild = true;
              installPhase = ''
                runHook preInstall
                mkdir -p $out/lib/lv2
                cp -r . $out/lib/lv2/demod_sierpinski_fx.lv2
                runHook postInstall
              '';
            })
          ];

          environment.variables.LV2_PATH = lib.mkDefault "/run/current-system/sw/lib/lv2";
        };
    };
}
