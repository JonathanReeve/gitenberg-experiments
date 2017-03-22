import glob
import yaml

repos = glob.glob('../repos/*')

t = repos[0]
yamlFilename = t + '/metadata.yaml'

with open(yamlFilename) as f: 
	metadata = f.read()

class LCC(yaml.YAMLObject):
	yaml_tag = u'!lcc'
        def __init__(self, name):
             self.name = name
        def __repr__(self):
            return "%s(name=%r)" % (
                self.__class__.__name__, self.name)

class LCSH(yaml.YAMLObject):
	yaml_tag = u'!lcsh'
        def __init__(self, name):
            self.name = name
        def __repr__(self):
            return "%s(name=%r)" % (
                self.__class__.__name__, self.name)

def ignore_tags(loader, tag_suffix, node):
        return tag_suffix + ' ' + node.value
   
add_multi_constructor('', default_ctor)

parsed = yaml.safe_load(metadata)

print(parsed)


