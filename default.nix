{ pkgs ? import (builtins.fetchTarball
  "https://github.com/nixos/nixpkgs-channels/archive/nixos-16.09.tar.gz") {}
, pythonPackages ? pkgs.python27Packages
}:

let self = {
  buildout = pythonPackages.zc_buildout_nix.overrideDerivation (old: {
    postInstall = "";
    propagatedNativeBuildInputs = with pythonPackages; [
      lxml
      pillow
    ];
  });
};

in pkgs.stdenv.mkDerivation rec {
  name = "env";
  buildInputs = with self; [ buildout ];
  shellHook = ''
    export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
    export BUILDOUT_ARGS="\
      versions:lxml= \
      versions:Pillow= \
      versions:python-ldap= \
      versions:setuptools= \
      versions:zc.buildout=
    "
  '';
}
