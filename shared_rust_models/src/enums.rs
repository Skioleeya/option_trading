use pyo3::prelude::*;

macro_rules! define_enum_class {
    ($name:ident, [$($value:ident),+ $(,)?]) => {
        #[pyclass(module = "shared_rust.models")]
        pub struct $name;

        #[pymethods]
        impl $name {
            $(
                #[classattr]
                pub const $value: &'static str = stringify!($value);
            )+
        }
    };
}

define_enum_class!(GexRegime, [SUPER_PIN, DAMPING, NEUTRAL, ACCELERATION]);
define_enum_class!(VannaFlowState, [DANGER_ZONE, GRIND_STABLE, NORMAL, VANNA_FLIP, UNAVAILABLE]);
define_enum_class!(
    VannaAccelerationState,
    [
        ACCELERATING_FEAR,
        DECELERATING_FEAR,
        REVERSING_UP,
        REVERSING_DOWN,
        ACCELERATING_CALM,
        DECELERATING_CALM,
        STABLE,
        UNAVAILABLE
    ]
);
define_enum_class!(
    IVVelocityState,
    [PAID_MOVE, ORGANIC_GRIND, HOLLOW_RISE, HOLLOW_DROP, PAID_DROP, VOL_EXPANSION, EXHAUSTION, UNAVAILABLE]
);
define_enum_class!(
    WallMigrationCallState,
    [RETREATING_RESISTANCE, REINFORCED_WALL, BREACHED, DECAYING, STABLE, UNAVAILABLE]
);
define_enum_class!(
    WallMigrationPutState,
    [RETREATING_SUPPORT, REINFORCED_SUPPORT, BREACHED, DECAYING, STABLE, UNAVAILABLE]
);
define_enum_class!(WallGammaRegime, [LONG_GAMMA, SHORT_GAMMA, NEUTRAL]);
define_enum_class!(IVRegime, [LOW, NORMAL, ELEVATED, HIGH, EXTREME]);
define_enum_class!(
    GexIntensity,
    [EXTREME_POSITIVE, STRONG_POSITIVE, MODERATE, NEUTRAL, STRONG_NEGATIVE, EXTREME_NEGATIVE]
);

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<GexRegime>()?;
    module.add_class::<VannaFlowState>()?;
    module.add_class::<VannaAccelerationState>()?;
    module.add_class::<IVVelocityState>()?;
    module.add_class::<WallMigrationCallState>()?;
    module.add_class::<WallMigrationPutState>()?;
    module.add_class::<WallGammaRegime>()?;
    module.add_class::<IVRegime>()?;
    module.add_class::<GexIntensity>()?;
    Ok(())
}
