import os
import xml.etree.ElementTree as ET
import zipfile


class Model:

    def __init__(self, ref):
        self.ref = ref
        self.language_usages = {}
        self.roots = []

    def add_language_usage(self, usage):
        self.language_usages[usage.id] = usage

    def add_devkit_usage(self, usage):
        pass

    def uuid(self):
        return self.ref[2:]

    def add_root_node(self, node):
        self.roots.append(node)


class LanguageUsage:

    def __init__(self, id, name, version):
        self.id = id
        self.name = name
        self.version = version


class LanguageDefinition:

    def __init__(self, namespace, uuid):
        self.namespace = namespace
        self.uuid = uuid


class Node:

    def __init__(self, id, concept_def):
        self.id = id
        self.concept_def = concept_def
        self.properties = {}
        self.references = {}
        self.children = {}

    def set_property(self, property_def, value):
        self.properties[property_def.id] = (property_def, value)

    def set_reference(self, reference_def, value_id, resolve):
        self.properties[reference_def.id] = (reference_def, value_id, resolve)

    def add_child(self, child_def, value):
        if child_def.id not in self.children:
            self.children[child_def.id] = (child_def, [])
        self.children[child_def.id][1].append(value)


class ModelReference:

    def __init__(self, ref, implicit):
        self.ref = ref
        self.implicit = implicit


class ImportingTable:

    def __init__(self):
        self.models = {}
        self.concepts = {}
        self.properties = {}
        self.children = {}
        self.references = {}

    def load_language(self, lang):
        for c_id in lang.concepts:
            c = lang.concepts[c_id]
            self.concepts[c.index] = c
            for p_id in c.properties:
                p = c.properties[p_id]
                self.properties[p.index] = p
            for r_id in c.references:
                r = c.references[r_id]
                self.references[r.index] = r
            for ch_id in c.children:
                ch = c.children[ch_id]
                self.children[ch.index] = ch

    def register_model(self, index, ref, implicit):
        self.models[index] = ModelReference(ref, implicit)

    def find_model(self, index):
        if index in self.models:
            return self.models[index]
        else:
            raise Exception("Model not found %s" % index)

    def find_concept(self, index):
        if index in self.concepts:
            return self.concepts[index]
        else:
            raise Exception("Concept not found %s" % index)

    def find_property(self, index):
        if index in self.properties:
            return self.properties[index]
        else:
            raise Exception("Property not found %s" % index)

    def find_child(self, index):
        if index in self.children:
            return self.children[index]
        else:
            raise Exception("Child relationship ot found %s" % index)

    def find_reference(self, index):
        if index in self.references:
            return self.references[index]
        else:
            raise Exception("Reference not found %s" % index)


class ImportedLanguage:

    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.concepts = {}

    def register_concept(self, concept):
        self.concepts[concept.id] = concept


class ImportedConcept:

    def __init__(self, id, name, flags, index):
        self.id = id
        self.name = name
        self.flags = flags
        self.index = index
        self.properties = {}
        self.children = {}
        self.references = {}

    def register_property(self, property):
        self.properties[property.id] = property

    def register_child(self, child):
        self.children[child.id] = child

    def register_reference(self, reference):
        self.references[reference.id] = reference


class ImportedConceptProperty:

    def __init__(self, id, name, index):
        self.id = id
        self.name = name
        self.index = index


class ImportedConceptChild:

    def __init__(self, id, name, index):
        self.id = id
        self.name = name
        self.index = index


class ImportedConceptReference:

    def __init__(self, id, name, index):
        self.id = id
        self.name = name
        self.index = index


class Environment:

    def __init__(self):
        self.verbose = False
        self.languages = {}
        self.models = {}

    def __log(self, message):
        if self.verbose:
            print("ENV %s" % message)

    def register_language(self, language_definition):
        self.languages[language_definition.uuid] = language_definition

    def __load_language_usage(self, node):
        return LanguageUsage(node.attrib['id'], node.attrib['name'], node.attrib['version'])

    def load_devkit_usage(self, node):
        pass

    def __load_node(self, xml_node, imp_table):
        id = xml_node.attrib['id']
        concept_index = xml_node.attrib['concept']
        concept_def = imp_table.find_concept(concept_index)
        node = Node(id, concept_def)
        for cn in xml_node:
            if cn.tag == 'property':
                property_index = cn.attrib['role']
                property_def = imp_table.find_property(property_index)
                node.set_property(property_def, cn.attrib['value'])
            elif cn.tag == 'ref':
                ref_index = cn.attrib['role']
                ref_def = imp_table.find_reference(ref_index)
                # instead of having the attribute 'node' a reference could have the attribute 'to'
                # in that case we need to add a reference to a node in another model
                if 'node' in cn.attrib:
                    node.set_reference(ref_def, cn.attrib['node'], cn.attrib['resolve'])
                elif 'to' in cn.attrib:
                    to = cn.attrib['to']
                    model_index, node_index = to.split(":", 1)
                    model_def = imp_table.find_model(model_index)
                else:
                    raise Exception()
            elif cn.tag == 'node':
                child_index = cn.attrib['role']
                child_def = imp_table.find_child(child_index)
                node.add_child(child_def, self.__load_node(cn, imp_table))
            else:
                raise Exception(cn.tag)
        return node

    def __load_imported_concept(self, xml_node):
        c = ImportedConcept(xml_node.attrib['id'], xml_node.attrib['name'], xml_node.attrib['flags'], xml_node.attrib['index'])
        #print("LOADING IMPORTED CONCEPT %s" % xml_node.attrib['id'])
        for child in xml_node:
            if child.tag == 'property':
                c.register_property(ImportedConceptProperty(child.attrib['id'], child.attrib['name'], child.attrib['index']))
            elif child.tag == 'child':
                c.register_child(ImportedConceptChild(child.attrib['id'], child.attrib['name'], child.attrib['index']))
            elif child.tag == 'reference':
                c.register_reference(ImportedConceptReference(child.attrib['id'], child.attrib['name'], child.attrib['index']))
            else:
                raise Exception(child.tag)
        return c

    def __load_imported_language(self, xml_node):
        lang = ImportedLanguage(xml_node.attrib['id'], xml_node.attrib['name'])
        #print("LOADING IMPORTED LANG %s" % xml_node.attrib['id'])
        for c in xml_node:
            lang.register_concept(self.__load_imported_concept(c))
        return lang

    def load_mps_file(self, path):
        #print(" MPS file %s" % path)
        tree = ET.parse(path)
        root = tree.getroot()
        model = Model(root.attrib['ref'])
        self.__log("Record model %s" % model.uuid())

        imp_table = ImportingTable()

        for language_node in root.find('languages'):
            if language_node.tag == 'use':
                model.add_language_usage(self.__load_language_usage(language_node))
            elif language_node.tag == 'devkit':
                model.add_devkit_usage((self.load_devkit_usage(language_node)))
            else:
                raise Exception("Unknown tag %s" % language_node.tag)
        imported_languages = [self.__load_imported_language(n) for n in root.find('registry')]
        for lang in imported_languages:
            imp_table.load_language(lang)

        for import_node in root.find('imports'):
            implicit = False
            if 'implicit' in import_node.attrib:
                implicit = import_node.attrib['implicit']
            imp_table.register_model(import_node.attrib['index'], import_node.attrib['ref'], implicit)

        for child in root:
            if child.tag == 'node':
                model.add_root_node(self.__load_node(child, imp_table))
        self.models[model.uuid()] = model

    def load_jar_file(self, path):
        #print("JAR %s" % path)
        zf = zipfile.ZipFile(path, 'r')
        module_entry = [zi for zi in zf.infolist() if zi.filename == "META-INF/module.xml"]
        if len(module_entry) == 1:
            data = zf.read("META-INF/module.xml")
            root = ET.fromstring(data)
            if root.attrib['type'] == 'language':
                language_def = LanguageDefinition(root.attrib['namespace'], root.attrib['uuid'])
                self.register_language(language_def)
            elif root.attrib['type'] == 'solution':
                pass
            else:
                raise Exception("Unknown type %s" % root.attrib['type'])

    def load_dir(self, path):
        for content in os.listdir(path):
            childname = os.path.join(path, content)
            if os.path.isdir(childname):
                self.load_dir(childname)
            else:
                filename, file_extension = os.path.splitext(childname)
                if file_extension == ".mps":
                    self.load_mps_file(childname)
                elif file_extension == ".jar":
                    self.load_jar_file(childname)

    def verify(self):
        pass


def main():
    environment = Environment()
    #environment.load_jar_file("/home/federico/tools/MPS3.3.4/languages/languageDesign/jetbrains.mps.lang.structure.jar")
    environment.load_dir("/home/federico/tools/MPS3.3.4")
    environment.verbose = True
    environment.load_dir("/home/federico/repos/mps-lwc-16")

if __name__ == '__main__':
    main()