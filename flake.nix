{
  description = "DeMoD Sierpinski FX System v2.4 — Argent Metal Edition";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python311;

        demod-beater = python.pkgs.buildPythonApplication {
          pname = "demod-sierpinski-beater";
          version = "2.4";
          src = ./.;
          pyproject = true;
          build-system = [ python.pkgs.setuptools ];
          propagatedBuildInputs = with python.pkgs; [ rich questionary pretty-midi soundfile numpy ];
          doCheck = false;
          meta.mainProgram = "demod-sierpinski-beater";
        };

        demod-fx = pkgs.stdenv.mkDerivation {
          pname = "demod-sierpinski-fx";
          version = "2.4";
          src = ./.;
          nativeBuildInputs = [ pkgs.faust pkgs.lv2 ];
          buildPhase = ''
            mkdir -p $out/lib/lv2
            faust2lv2 -a -t "DeMoD Sierpinski FX" demod_sierpinski_fx.dsp
            mv demod_sierpinski_fx.lv2 $out/lib/lv2/

            faust2jack demod_sierpinski_fx.dsp
            mkdir -p $out/bin
            mv demod_sierpinski_fx $out/bin/demod-sierpinski-fx-jack
          '';
          installPhase = "true";
        };

      in {
        packages = {
          default = demod-beater;
          beater = demod-beater;
          fx-lv2 = demod-fx;
          fx-jack = pkgs.runCommand "demod-sierpinski-fx-jack" {} ''
            mkdir -p $out/bin
            ln -s ${demod-fx}/bin/demod-sierpinski-fx-jack $out/bin/
          '';
        };

        apps.default.program = "${demod-beater}/bin/demod-sierpinski-beater";

        devShells.default = pkgs.mkShell {
          buildInputs = [
            demod-beater pkgs.faust pkgs.fluidsynth pkgs.lv2 pkgs.jack2 pkgs.qjackctl
            python.pkgs.black python.pkgs.ruff
          ];
          shellHook = ''
            echo "🚀 DeMoD Sierpinski Argent Metal Edition v2.4 loaded"
            echo "   Run: demod-sierpinski-beater"
          '';
        };
      }
    ) // {
      nixosModules.default = { ... }: {
        environment.systemPackages = [ self.packages.${pkgs.system}.beater self.packages.${pkgs.system}.fx-jack ];
        environment.variables.LV2_PATH = "/run/current-system/sw/lib/lv2";
      };
    };
}