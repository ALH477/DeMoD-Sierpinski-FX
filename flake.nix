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
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python311;
        in
        {
          beater = python.pkgs.buildPythonApplication {
            pname = "demod-sierpinski-beater";
            version = "2.4";
            src = ./.;
            pyproject = true;
            build-system = [ python.pkgs.setuptools ];
            propagatedBuildInputs = with python.pkgs; [
              rich
              questionary
              pretty-midi
              soundfile
              numpy
            ];
            doCheck = false;
          };

          fx-lv2 = pkgs.stdenv.mkDerivation {
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
        }
      );

      defaultPackage = forAllSystems (system: self.packages.${system}.beater);

      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python311;
        in
        {
          default = pkgs.mkShell {
            buildInputs = [
              (python.pkgs.buildPythonApplication {
                pname = "demod-sierpinski-beater";
                version = "2.4";
                src = ./.;
                pyproject = true;
                build-system = [ python.pkgs.setuptools ];
                propagatedBuildInputs = with python.pkgs; [
                  rich
                  questionary
                  pretty-midi
                  soundfile
                  numpy
                ];
                doCheck = false;
              })
              pkgs.faust
              pkgs.fluidsynth
              pkgs.lv2
              pkgs.jack2
              python.pkgs.black
              python.pkgs.ruff
            ];
            shellHook = ''
              echo "DeMoD Sierpinski Argent Metal Edition v2.4 loaded"
              echo "   Run: demod-sierpinski-beater"
            '';
          };
        }
      );

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.beater}/bin/demod-sierpinski-beater";
        };
      });

      nixosModules.default = { lib, ... }: {
        nixos = {
          environment.systemPackages = let
            pkgSet = nixpkgs.legacyPackages.x86_64-linux;
          in [
            (pkgSet.python311.pkgs.buildPythonApplication {
              pname = "demod-sierpinski-beater";
              version = "2.4";
              src = ./.;
              pyproject = true;
              build-system = [ pkgSet.python311.pkgs.setuptools ];
              propagatedBuildInputs = with pkgSet.python311.pkgs; [
                rich
                questionary
                pretty-midi
                soundfile
                numpy
              ];
              doCheck = false;
            })
          ];
          environment.variables.LV2_PATH = "/run/current-system/sw/lib/lv2";
        };
      };
    };
}
