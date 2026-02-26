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
          beater = pkgs.writeShellScriptBin "demod-sierpinski-beater" ''
            exec ${python.interpreter} -m pip install --quiet --break-system-packages rich questionary pretty-midi soundfile numpy
            exec ${python.interpreter} -c "from demod_sierpinski_beater import main; main()"
          '';

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
              python
              pkgs.pip
              pkgs.faust
              pkgs.fluidsynth
              pkgs.lv2
              pkgs.jack2
              python.pkgs.black
              python.pkgs.ruff
            ];
            shellHook = ''
              pip install --quiet --break-system-packages rich questionary pretty-midi soundfile numpy
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
            pkgSet.python311
            (pkgSet.writeShellScriptBin "demod-sierpinski-beater" ''
              exec ${pkgSet.python311.interpreter} -m pip install --quiet --break-system-packages rich questionary pretty-midi soundfile numpy
              exec ${pkgSet.python311.interpreter} -c "from demod_sierpinski_beater import main; main()"
            '')
          ];
          environment.variables.LV2_PATH = "/run/current-system/sw/lib/lv2";
        };
      };
    };
}
