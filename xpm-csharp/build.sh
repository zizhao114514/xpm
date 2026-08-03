#!/bin/sh
# build.sh - Compile xmcs (XPM C# Backend Special Edition)
set -e

OUT="xmcs"
SRC="src/Program.cs src/Xm.cs src/LockFile.cs src/OilPackage.cs src/Transaction.cs src/Coffee.cs src/DpkgWrapper.cs"

# Try dotnet first, fallback to mcs
if command -v dotnet >/dev/null 2>&1; then
    echo "  Using: dotnet SDK"
    dotnet build -c Release -o ./bin 2>/dev/null || true
    if [ -f "./bin/Program" ]; then
        cp "./bin/Program" "$OUT"
    elif [ -f "./bin/xmcs" ]; then
        cp "./bin/xmcs" "$OUT"
    fi
fi

# Fallback: mcs (Mono C# compiler)
if [ ! -f "$OUT" ] && command -v mcs >/dev/null 2>&1; then
    echo "  Using: mcs (Mono)"
    mcs -out:$OUT $SRC -target:exe -optimize+
fi

# Fallback: csc (Microsoft .NET compiler)
if [ ! -f "$OUT" ] && command -v csc >/dev/null 2>&1; then
    echo "  Using: csc"
    csc -out:$OUT $SRC -optimize
fi

if [ -f "$OUT" ]; then
    chmod +x "$OUT"
    echo "✅ Built: $OUT ($(wc -c < $OUT) bytes)"
    echo "☕ Oil reserve: 100001%"
    echo "🛢️ Power: 1.x W"
else
    echo "❌ Build failed: no C# compiler found"
    echo "   Install one of: dotnet-sdk / mono-mcs / dotnet-runtime"
    exit 1
fi
