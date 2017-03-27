import glob
import yaml
import pandas as pd
import json

# Ignore special handling of tags like !lcsh
def default_ctor(loader, tag_suffix, node):
    # print(loader, tag_suffix, node)
    return tag_suffix + ' ' + node.value

yaml.add_multi_constructor('', default_ctor)

repos = glob.glob('/run/media/jon/SAMSUNG/gitenberg/*')

def loadYaml(path):
    yamlFilename = path + '/metadata.yaml'
    try:
        with open(yamlFilename) as f:
            metadata = f.read()
    except:
        return None
    return metadata

def parseYaml(metadata):
    parsed = yaml.load(metadata)
    return parsed

def loadJson(path):
    jsonFilename = path + '/metadata.json'
    try:
        with open(jsonFilename) as f:
            metadata = f.read()
    except:
        return None
    return metadata

def parseJson(metadata):
    try:
        parsed = json.loads(metadata)
    except:
        print("Couldn't parse JSON for some reason.")
        return None
    return parsed

gitenbergDict = {}
for i, repo in enumerate(repos):
    repoLen = len(repos)
    print('Processing %s of %s: %s' % (i, repoLen, repo))
    print('Processing: ', repo)
    repoID = repo.split('_')[-1]
    metadata = loadYaml(repo)
    jsonMetadata = loadJson(repo)
    if metadata is not None:
        metadata = parseYaml(metadata)
        print('Successfully parsed YAML.')
    else:
        print("ERROR: Couldn't parse YAML.")
        metadata = {}
    if jsonMetadata is not None:
        jsonParsed = parseJson(jsonMetadata)
        print('Successfully parsed JSON.')
    else:
        print("ERROR: Couldn't load JSON.")
        jsonParsed = {}
    if jsonParsed is not None: 
        # Merge
        for key in jsonParsed:
            prefixed = 'j' + key
            metadata[prefixed] = jsonParsed[key]
    gitenbergDict[repoID] = metadata
    # if i > 100:
        # break

print('Making data frame...')
df = pd.DataFrame(gitenbergDict).T

print('Writing to csv...')
df.to_csv('gitenberg-metadata.csv')
