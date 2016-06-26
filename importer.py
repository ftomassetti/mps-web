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

    def set_property(self, property_def, value):
        self.properties[property_def.id] = (property_def, value)
        

class ImportingTable:

    def __init__(self):
        self.concepts = {}
        self.properties = {}

    def find_property(self, index):
        if index in self.properties:
            return self.properties[index]
        else:
            raise Exception("Property not found %s" % index)

    def load_language(self, lang):
        for c_id in lang.concepts:
            c = lang.concepts[c_id]
            self.concepts[c.index] = c
            for p_id in c.properties:
                p = c.properties[p_id]
                self.properties[p.index] = p

    def find_concept(self, index):
        if index in self.concepts:
            return self.concepts[index]
        else:
            raise Exception("Not found %s" % index)


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

    def register_property(self, property):
        self.properties[property.id] = property

    def register_child(self, child):
        pass

    def register_reference(self, child):
        pass


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
                pass
            elif cn.tag == 'node':
                pass
            else:
                raise Exception(cn.tag)

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
        languages_node = root.find('languages')
        for language_node in languages_node:
            if language_node.tag == 'use':
                model.add_language_usage(self.__load_language_usage(language_node))
            elif language_node.tag == 'devkit':
                model.add_devkit_usage((self.load_devkit_usage(language_node)))
            else:
                raise Exception("Unknown tag %s" % language_node.tag)

        imported_languages = [self.__load_imported_language(n) for n in root.find('registry')]
        imp_table = ImportingTable()
        for lang in imported_languages:
            imp_table.load_language(lang)

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