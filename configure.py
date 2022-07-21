import os
import subprocess
import sys
from glob import glob
from textwrap import dedent


def xcode_select_path():
    return subprocess.run(
        ["xcode-select", "--print-path"], capture_output=True, text=True
    ).stdout.rstrip()


def make_sdk_path(sdk_name, xcode_path):
    return f"{xcode_path}/Platforms/{sdk_name}.platform/Developer/SDKs/{sdk_name}.sdk"


def framework_path(sdk_path):
    return f"{sdk_path}/System/Library/Frameworks"


def find_framework_names(sdk_path):
    f_path = framework_path(sdk_path)
    pattern = f_path + "/*.framework"
    # print(pattern)
    for f in glob(pattern):
        name = os.path.basename(f).removesuffix(".framework")
        if name.startswith("_"):
            continue
        yield name


def gen_lib(names):
    source = dedent(
        f"""
    //! apple-sys main module
    //! auto-generated by "python {" ".join(map(repr, sys.argv))}"
    #![allow(dead_code)]
    #![allow(non_camel_case_types)]
    #![allow(non_upper_case_globals)]
    #![allow(improper_ctypes)]
    #![allow(non_snake_case)]
    
    """
    )

    def gen_module(name):
        return f"""#[cfg(feature = "{name}")] pub mod {name} {{ include!(concat!(env!("OUT_DIR"), "/{name}.rs"));  }}"""

    source += "\n".join(gen_module(name) for name in names)

    return source


def gen_cargo(names):
    DELIMITER = "# AUTO-GENERATED: DO NOT ADD ANYTHING BELOW THIS LINE"
    source = open("Cargo.toml", "r").read()
    top, _ = source.split(DELIMITER)
    return f"""{top}{DELIMITER}\n""" + "\n".join(f"{name} = []" for name in names)


def gen_build(names):
    body = "\n".join(f"""#[cfg(feature = "{name}")] "{name}",""" for name in names)
    return f"""vec![
        {body}
    ]"""


def main(sdk_name):
    xcode_path = os.environ.get("XCODE_PATH") or xcode_select_path()
    sdk_path = make_sdk_path(sdk_name, xcode_path)
    framework_names = sorted(find_framework_names(sdk_path))

    with open("src/lib.rs", "w") as f:
        content = gen_lib(framework_names)
        f.write(content)

    content = gen_cargo(framework_names)
    with open("Cargo.toml", "w") as f:
        f.write(content)

    with open("build_features.inc.rs", "w") as f:
        content = gen_build(framework_names)
        f.write(content)


if __name__ == "__main__":
    main("MacOSX")


def test_xcode_select_path():
    assert xcode_select_path().endswith("/Developer")


# FRAMEWORK_PATH="${XCODE_PATH}/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks"
# echo "listing from ${FRAMEWORK_PATH}"

# for framework in "${FRAMEWORK_PATH}"/*.framework; do
# 	framework=${framework##*/}
# 	name=${framework%.framework}
# 	echo $name
# done