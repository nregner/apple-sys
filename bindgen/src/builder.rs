pub use crate::{
    config::{Config, ConfigMap, FileConfig},
    sdk::{SdkPath, SdkPathError},
};

#[derive(Debug)]
pub struct Builder {
    framework: String,
    sdk: Option<SdkPath>,
    target: Option<String>,
    config: Config,
}

impl Builder {
    pub fn new(framework: &str, config: Config) -> Self {
        Self {
            framework: framework.to_owned(),
            sdk: None,
            target: None,
            config,
        }
    }

    pub fn with_builtin_config(framework: &str) -> Self {
        let framework = framework;
        Self::new(framework, ConfigMap::with_builtin_config().build(framework))
    }

    pub fn sdk(
        mut self,
        path: impl TryInto<SdkPath, Error = SdkPathError>,
    ) -> Result<Self, SdkPathError> {
        assert!(self.sdk.is_none());
        self.sdk = Some(path.try_into()?);
        Ok(self)
    }

    pub fn target(mut self, target: impl AsRef<str>) -> Self {
        assert!(self.target.is_none());
        self.target = Some(target.as_ref().to_owned());
        self
    }

    pub fn bindgen_builder(&self) -> bindgen::Builder {
        // Begin building the bindgen params.
        let mut builder = bindgen::Builder::default();

        let mut clang_args = vec!["-x", "objective-c", "-fblocks", "-fmodules"];
        let target_arg;
        if let Some(target) = self.target.as_ref() {
            target_arg = format!("--target={}", target);
            clang_args.push(&target_arg);
        }

        let sdk = self.sdk.as_ref().expect("sdk is not set");
        clang_args.extend(&["-isysroot", sdk.path().to_str().unwrap()]);

        builder = builder
            .clang_args(&clang_args)
            .layout_tests(self.config.layout_tests)
            .rustfmt_bindings(true);

        for opaque_type in &self.config.opaque_types {
            builder = builder.opaque_type(opaque_type);
        }
        for blocklist_item in &self.config.blocklist_items {
            builder = builder.blocklist_item(blocklist_item);
        }

        builder = builder.header_contents(
            &format!("{}.h", self.framework),
            &format!("@import {};", self.framework),
        );

        builder
    }

    pub fn generate(&self) -> String {
        let bindgen_builder = self.bindgen_builder();

        // Generate the bindings.
        let bindings = bindgen_builder
            .generate()
            .expect("unable to generate bindings");

        // TODO: find the best way to do this post-processing
        let mut out = bindings.to_string();
        for replacement in &self.config.replacements {
            let (old, new) = replacement
                .split_once(" #=># ")
                .expect("Bindgen.toml is malformed");
            out = out.replace(old, new);
        }
        out
    }
}
