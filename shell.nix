{ pkgs ? import <nixpkgs> {} }:

let
  fatest = import ./default.nix { inherit pkgs; };
in
pkgs.mkShell {
  buildInputs = [
    fatest
    (pkgs.python3.withPackages (ps: with ps; [
      rich
      speedtest-cli
      psutil
      setuptools
    ]))
  ];

  shellHook = ''
    echo "fatest dev shell ready. Just run: fatest"
  '';
}
