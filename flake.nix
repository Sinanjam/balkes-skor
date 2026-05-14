{
  description = "Balkes Skor local tooling (NixOS/Fish friendly)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config = {
              allowUnfree = true;
              android_sdk.accept_license = true;
            };
          };
          pythonEnv = pkgs.python312.withPackages (ps: with ps; [
            beautifulsoup4
            lxml
          ]);
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              pythonEnv
              fish
              git
              jq
              zip
              unzip
              coreutils
              findutils
            ];
            shellHook = ''
              echo "Balkes Skor shell hazır. Örnek: fish run_tff_factory.fish 2018-2019 5 350"
            '';
          };
        });
    };
}
