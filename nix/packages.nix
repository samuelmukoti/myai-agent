# nix/packages.nix — MyAIOne Agent package built with uv2nix
{ inputs, ... }:
{
  perSystem =
    { pkgs, inputs', ... }:
    let
      hermesVenv = pkgs.callPackage ./python.nix {
        inherit (inputs) uv2nix pyproject-nix pyproject-build-systems;
      };

      hermesTui = pkgs.callPackage ./tui.nix {
        npm-lockfile-fix = inputs'.npm-lockfile-fix.packages.default;
      };

      # Import bundled skills, excluding runtime caches
      bundledSkills = pkgs.lib.cleanSourceWith {
        src = ../skills;
        filter = path: _type: !(pkgs.lib.hasInfix "/index-cache/" path);
      };

      hermesWeb = pkgs.callPackage ./web.nix {
        npm-lockfile-fix = inputs'.npm-lockfile-fix.packages.default;
      };

      runtimeDeps = with pkgs; [
        nodejs_22
        ripgrep
        git
        openssh
        ffmpeg
        tirith
      ];

      runtimePath = pkgs.lib.makeBinPath runtimeDeps;

      # Lockfile hashes for dev shell stamps
      pyprojectHash = builtins.hashString "sha256" (builtins.readFile ../pyproject.toml);
      uvLockHash =
        if builtins.pathExists ../uv.lock then
          builtins.hashString "sha256" (builtins.readFile ../uv.lock)
        else
          "none";
    in
    {
      packages = {
        default = pkgs.stdenv.mkDerivation {
          pname = "hermes-agent";
          version = (fromTOML (builtins.readFile ../pyproject.toml)).project.version;

          dontUnpack = true;
          dontBuild = true;
          nativeBuildInputs = [ pkgs.makeWrapper ];

          installPhase = ''
            runHook preInstall

            mkdir -p $out/share/myai-agent $out/bin
            cp -r ${bundledSkills} $out/share/myai-agent/skills
            cp -r ${hermesWeb} $out/share/myai-agent/web_dist

            # copy pre-built TUI (same layout as dev: ui-tui/dist/ + node_modules/)
            mkdir -p $out/ui-tui
            cp -r ${hermesTui}/lib/hermes-tui/* $out/ui-tui/

            ${pkgs.lib.concatMapStringsSep "\n"
              (name: ''
                makeWrapper ${hermesVenv}/bin/${name} $out/bin/${name} \
                  --suffix PATH : "${runtimePath}" \
                  --set MYAI_AGENT_BUNDLED_SKILLS $out/share/myai-agent/skills \
                  --set MYAI_AGENT_WEB_DIST $out/share/myai-agent/web_dist \
                  --set MYAI_AGENT_TUI_DIR $out/ui-tui \
                  --set MYAI_AGENT_PYTHON ${hermesVenv}/bin/python3 \
                  --set MYAI_AGENT_NODE ${pkgs.nodejs_22}/bin/node
              '')
              [
                "hermes"
                "hermes-agent"
                "hermes-acp"
              ]
            }

            runHook postInstall
          '';

          passthru.devShellHook = ''
            STAMP=".nix-stamps/myai-agent"
            STAMP_VALUE="${pyprojectHash}:${uvLockHash}"
            if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$STAMP_VALUE" ]; then
              echo "hermes-agent: installing Python dependencies..."
              uv venv .venv --python ${pkgs.python312}/bin/python3 2>/dev/null || true
              source .venv/bin/activate
              uv pip install -e ".[all]"
              [ -d mini-swe-agent ] && uv pip install -e ./mini-swe-agent 2>/dev/null || true
              [ -d tinker-atropos ] && uv pip install -e ./tinker-atropos 2>/dev/null || true
              mkdir -p .nix-stamps
              echo "$STAMP_VALUE" > "$STAMP"
            else
              source .venv/bin/activate
              export MYAI_AGENT_PYTHON=${hermesVenv}/bin/python3
            fi
          '';

          meta = with pkgs.lib; {
            description = "AI agent with advanced tool-calling capabilities";
            homepage = "https://github.com/NousResearch/hermes-agent";
            mainProgram = "hermes";
            license = licenses.mit;
            platforms = platforms.unix;
          };
        };

        tui = hermesTui;
        web = hermesWeb;
      };
    };
}
