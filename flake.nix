{
  description = "FaTest - a fast, clean terminal speedtest tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        fatest = pkgs.callPackage ./default.nix { };
      in
      {
        packages.default = fatest;
        packages.fatest = fatest;

        apps.default = {
          type = "app";
          program = "${fatest}/bin/fatest";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [ fatest ];
        };
      }
    );
}
