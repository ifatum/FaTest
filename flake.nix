{
  description = "FaTest - a fast, clean terminal speedtest tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f system);
    in
    {
      packages = forEachSystem (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };

          fatest = pkgs.callPackage ./default.nix { };
        in
        {
          default = fatest;
          fatest = fatest;
        }
      );

      apps = forEachSystem (
        system:
        let
          fatest = self.packages.${system}.default;
        in
        {
          default = {
            type = "app";
            program = "${fatest}/bin/fatest";
          };
        }
      );

      devShells = forEachSystem (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };

          fatest = pkgs.callPackage ./default.nix { };
        in
        {
          default = pkgs.mkShell {
            buildInputs = [ fatest ];
          };
        }
      );
    };
}
