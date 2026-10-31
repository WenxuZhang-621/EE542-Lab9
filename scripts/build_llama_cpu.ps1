param(
    [Parameter(Mandatory=$true)][string]$SourcePath,
    [Parameter(Mandatory=$true)][string]$CompilerBin,
    [string]$CMakePath = 'cmake',
    [string]$NinjaPath = 'ninja',
    [int]$Jobs = 4
)
$ErrorActionPreference = 'Stop'
$labSource = (Resolve-Path -LiteralPath $SourcePath).Path
$labCompiler = (Resolve-Path -LiteralPath $CompilerBin).Path
$labCmake = (Get-Command $CMakePath -ErrorAction Stop).Source
$labNinja = (Get-Command $NinjaPath -ErrorAction Stop).Source
$labBuild = Join-Path $labSource 'build-cpu'
$labCommit = (& git -C $labSource rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'SourcePath must be a llama.cpp Git checkout.' }
if ($labCommit -ne 'f3586e66bc916d672773d4a6505513ba91a3595c') {
    throw 'Use the validated llama.cpp b12023 commit f3586e66bc916d672773d4a6505513ba91a3595c.'
}
if ($Jobs -lt 1) { throw 'Jobs must be positive.' }
$labOldPath = $env:Path
try {
    $env:Path = $labCompiler + ';' + (Split-Path $labNinja -Parent) + ';' + $env:Path
    $labFlags = @(
        '-S', $labSource, '-B', $labBuild, '-G', 'Ninja',
        '-DCMAKE_BUILD_TYPE=Release', ('-DCMAKE_MAKE_PROGRAM=' + $labNinja),
        ('-DCMAKE_C_COMPILER=' + (Join-Path $labCompiler 'x86_64-w64-mingw32-clang.exe')),
        ('-DCMAKE_CXX_COMPILER=' + (Join-Path $labCompiler 'x86_64-w64-mingw32-clang++.exe')),
        '-DCMAKE_C_FLAGS=-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00',
        '-DCMAKE_CXX_FLAGS=-D_WIN32_WINNT=0x0A00 -DWINVER=0x0A00',
        '-DGGML_CUDA=OFF', '-DGGML_NATIVE=ON', '-DGGML_OPENMP=OFF',
        '-DLLAMA_OPENSSL=OFF', '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF',
        '-DLLAMA_BUILD_APP=OFF', '-DLLAMA_USE_PREBUILT_UI=OFF', '-DLLAMA_BUILD_UI=OFF',
        '-DBUILD_SHARED_LIBS=OFF', '-DCMAKE_OBJECT_PATH_MAX=240'
    )
    & $labCmake @labFlags
    if ($LASTEXITCODE -ne 0) { throw 'llama.cpp configuration failed.' }
    & $labCmake --build $labBuild --target llama-server --parallel $Jobs
    if ($LASTEXITCODE -ne 0) { throw 'llama.cpp build failed.' }
    # The MinGW executable needs these compiler-runtime DLLs beside it.
    foreach ($labDll in @('libc++.dll','libunwind.dll','libwinpthread-1.dll')) {
        $labDllPath = Join-Path $labCompiler $labDll
        if (Test-Path -LiteralPath $labDllPath) {
            Copy-Item -LiteralPath $labDllPath -Destination (Join-Path $labBuild 'bin') -Force
        }
    }
    & (Join-Path $labBuild 'bin\llama-server.exe') --version
    if ($LASTEXITCODE -ne 0) { throw 'Built server did not start.' }
} finally { $env:Path = $labOldPath }
