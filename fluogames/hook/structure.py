
from class_tools import Extensible, MetaProperty


class Structure(Extensible):

    def __wrap_metaprop__(self, name, prop):
        if isinstance(prop, MetaProperty):
            prop.name = "_"+name
            setattr(self, "_"+name, 
            return prop


