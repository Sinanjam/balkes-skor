{ pkgs ? import <nixpkgs> {
    config = {
      allowUnfree = true;
      android_sdk.accept_license = true;
    };
  }
}:

let
  androidComposition = pkgs.androidenv.composeAndroidPackages {
    platformVersions = [ "35" ];
    buildToolsVersions = [ "34.0.0" "35.0.0" ];
    includeEmulator = false;
    includeNDK = false;
    includeSystemImages = false;
  };
  androidSdk = androidComposition.androidsdk;
in
pkgs.mkShell {
  packages = with pkgs; [
    jdk17
    gradle
    git
    gh
    rsync
    zip
    unzip
    coreutils
    findutils
  ] ++ [ androidSdk ];

  ANDROID_HOME = "${androidSdk}/libexec/android-sdk";
  ANDROID_SDK_ROOT = "${androidSdk}/libexec/android-sdk";
  JAVA_HOME = "${pkgs.jdk17}";
}
