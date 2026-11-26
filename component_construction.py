class ComponentConstruction:
    """Keep the original constructor call, retaining argument values by reference."""

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance._component_constructor_call = (args, kwargs.copy())
        return instance
