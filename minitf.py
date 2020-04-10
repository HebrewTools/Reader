from functools import reduce

from tf.core.api import NodeFeature, EdgeFeature

class MiniApi(object):
    def __init__(
            self,
            nodes=None,
            features={},
            featureType={},
            locality={},
            text={},
            langs=set()):
        self.nodes = () if nodes is None else tuple(nodes)
        self.F = NodeFeatures()
        self.E = EdgeFeatures()

        rank = {n: i for (i, n) in enumerate(self.nodes)}
        self.rank = rank
        self.sortKey = lambda n: rank[n]

        for f in features:
            fType = featureType[f]
            if fType:
                fObj = EdgeFeature(self, None, features[f], fType == 1)
                setattr(self.E, f, fObj)
            else:
                fObj = NodeFeature(self, None, features[f])
                setattr(self.F, f, fObj)

        self.L = Locality(self, locality)
        self.T = Text(self, text, langs)

    def Fs(self, fName):
        return getattr(self.F, fName, None)

    def Es(self, fName):
        return getattr(self.E, fName, None)

    def Fall(self):
        return sorted(x[0] for x in self.F.__dict__.items())

    def Eall(self):
        return sorted(x[0] for x in self.E.__dict__.items())

    def N(self):
        for n in self.nodes:
            yield n

    def sortNodes(self, nodeSet):
        return sorted(nodeSet, key=self.sortKey)


class NodeFeatures(object):
    pass


class EdgeFeatures(object):
    pass


class Locality(object):
    def __init__(self, api, data):
        self.api = api
        self.data = data
        for member in ('u', 'd', 'n', 'p'):
            _makeLmember(self, member)


class Text(object):
    def __init__(self, api, langs, text):
        self.api = api
        self.langs = langs
        self.formats = set(text)
        self.data = text

    def text(self, slots, fmt=None):
        if fmt is None:
            fmt = DEFAULT_FORMAT
        thisText = self.data.get(fmt, None)
        if thisText is None:
            return ' '.join(str(s) for s in slots)
        return ''.join(thisText.get(s, '?') for s in slots)


def _makeLmember(dest, member):
    def memberFunction(n, otype=None):
        data = dest.data
        if n not in data.get(member, {}):
            return ()
        ms = data[member][n]
        if otype is None:
            return ms
        api = dest.api
        F = api.F
        return tuple(m for m in ms if F.otype.v(m) == otype)

    setattr(dest, member, memberFunction)


def gather_context(api, context, results):
    F = api.F
    Fs = api.Fs
    Es = api.Es
    L = api.L
    T = api.T
    TF = api.TF
    sortNodes = api.sortNodes

    # quit quickly if no context is required
    if not context or not results:
        return {}

    # parse the context requirements
    if context is True:
        langs = True
        featureSpec = True
        doLocality = True
        textFormats = True
    else:
        langs = context.get('languages', set())
        featureSpec = context.get('features', set())
        doLocality = context.get('locality', False)
        textFormats = context.get('formats', set())

    if type(langs) is str:
        langs = set(langs.strip().split())
    elif langs is True:
        langs = set(T.languages)

    if type(featureSpec) is str:
        featureSpec = set(featureSpec.strip().split())
    elif featureSpec is True:
        featureSpec = {f[0] for f in TF.features.items() if not (f[1].isConfig or f[1].method)}
    else:
        featureSpec = {fName for fName in featureSpec}

    testLangs = langs | {None}
    featureSpec = {fName for fName in featureSpec if _depLang(fName) in testLangs}

    if type(textFormats) is str:
        textFormats = set(textFormats.strip().split())
    elif textFormats is True:
        textFormats = T.formats

    # generate context: features

    loadedFeatures = api.ensureLoaded(featureSpec)
    allNodes = reduce(
            set.union,
            (set(r) for r in results),
            set(),
    )
    features = {}
    featureType = {}
    for f in sorted(loadedFeatures):
        fObj = TF.features[f]
        isEdge = fObj.isEdge
        isNode = not (isEdge or fObj.isConfig or fObj.method)
        if isNode:
            featureType[f] = 0
            data = {}
            for n in allNodes:
                val = Fs(f).v(n)
                if val is not None:
                    data[n] = val
            features[f] = data
        elif isEdge:
            if f == 'oslots':
                featureType[f] = -1
                data = {}
                for n in allNodes:
                    vals = tuple(m for m in Es(f).s(n) if m in allNodes)
                    if vals:
                        data[n] = vals
                features[f] = data
            else:
                hasValues = TF.features[f].edgeValues
                featureType[f] = 1 if hasValues else -1
                dataF = {}
                dataT = {}
                if hasValues:
                    for n in allNodes:
                        valsF = tuple(x for x in Es(f).f(n) if x[0] in allNodes)
                        valsT = tuple(x for x in Es(f).t(n) if x[0] in allNodes)
                        if valsF:
                            dataF[n] = valsF
                        if valsT:
                            dataT[n] = valsT
                else:
                    for n in allNodes:
                        valsF = tuple(m for m in Es(f).f(n) if m in allNodes)
                        valsT = tuple(m for m in Es(f).t(n) if m in allNodes)
                        if valsF:
                            dataF[n] = valsF
                        if valsT:
                            dataT[n] = valsT
                features[f] = (dataF, dataT)

    # generate context: locality

    locality = {}
    if doLocality:
        lu = {}
        ld = {}
        ln = {}
        lp = {}
        for n in allNodes:
            lu[n] = tuple(m for m in L.u(n) if m in allNodes)
            ld[n] = tuple(m for m in L.d(n) if m in allNodes)
            ln[n] = tuple(m for m in L.n(n) if m in allNodes)
            lp[n] = tuple(m for m in L.p(n) if m in allNodes)
        locality['u'] = lu
        locality['d'] = ld
        locality['n'] = ln
        locality['p'] = lp

    # generate context: formats

    slotType = F.otype.slotType
    text = {}
    slots = sorted(n for n in allNodes if F.otype.v(n) == slotType)
    for fmt in textFormats:
        data = {}
        for n in slots:
            data[n] = T.text([n], fmt=fmt)
        text[fmt] = data

    return dict(
            nodes=','.join(str(n) for n in sortNodes(allNodes)),
            features=features,
            featureType=featureType,
            locality=locality,
            text=text,
            langs=langs,
    )


def _depLang(feature):
    if '@' not in feature:
        return None
    else:
        return feature.rsplit('@', 1)[1]
