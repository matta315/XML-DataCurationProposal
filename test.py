from xml.dom import minidom
from xml.dom.minidom import Node

from lxml import etree
import xml.etree.ElementTree as ET
from io import StringIO, BytesIO
import hashlib


def normalize_line_ends(txt: str) -> str:
    pts = txt.split('\n')
    pts = [ss.strip() for ss in pts]
    return ' '.join(pts)


def trim_and_sort_attrs(tt: ET) -> None:
    for k in tt.attrib:
        tt.attrib[k] = tt.attrib[k].strip()
    dd = {}
    for k in tt.attrib:
        v = tt.attrib.pop(k)
        dd[k] = v
    for k in sorted(dd):
        tt.attrib[k] = dd[k]


def uniform_yes_no(tt: ET) -> None:
    for k in tt.attrib:
        v = tt.attrib[k]
        if v.lower() == 'y' or v.lower() == 'yes':
            tt.attrib[k] = 'Y'
        elif v.lower() == 'n' or v.lower() == 'no':
            tt.attrib[k] = 'N'


def sort_child_elements(tt: ET, key_func) -> None:
    if not tt[:]:
        return
    #print("debug = ", tt)
    #print("its children = ", tt[:])
    #tt[:] = sorted(tt, key=lambda x: x.tag)
    tt[:] = sorted(tt, key=key_func)
    for child in tt[:]:
        sort_child_elements(child, key_func)
    pass


def canonicalize_utf8_encoded(ff_path: str) -> bytearray:
    # Use an XML parser to read the intrinsic content of file
    # - Unify encoding to UTF-8
    # - Expand all attributes if there's any internal DTD
    # - Remove comment elements
    # - set load_dtd=False to remove internal schema/declarations
    parser = etree.XMLParser(encoding='utf8', attribute_defaults=True, remove_comments=True, load_dtd=False)
    complaintsRoot = etree.parse(ff_path, parser=parser).getroot()
    #str = ET.tostring(complaintsRoot, encoding='utf8').decode('utf8')

    # trim all texts - remove insignificant white spaces
    for elem in complaintsRoot.iter('*'):
        if elem.text:
            #print(elem.text)
            elem.text = elem.text.strip()
    # normalize line-ends in free-text fields
    for elem in complaintsRoot.iter('consumerNarrative'):
        elem.text = normalize_line_ends(elem.text)
    for elem in complaintsRoot.iter('publicResponse'):
        elem.text = normalize_line_ends(elem.text)

    # for any element, sort attributes & trim their values
    for anyTag in complaintsRoot.iter('*'):
        trim_and_sort_attrs(anyTag)
    # sort elements at all levels (starting from level=complaint) by tag name alphabetically
    sort_child_elements(complaintsRoot[:], lambda x: x.tag)

    # re-format data in old system -> new format
    # for every complaint, replace attribute 'submitted' by element 'submissionType'
    for complaint in complaintsRoot.iter('complaint'):
        subs = [sub for sub in complaint.iter('submitted')]
        if subs:
            assert 1 == len(subs)
            # E.g.: Change <submitted via='Web'> to attribute submissionType='Web'
            if 'via' in subs[0].attrib:
                submType = subs[0].attrib['via']
                complaint.attrib['submissionType'] = submType
            # remove the <submitted /> element
            complaint.remove(subs[0])

    # uniform response - yes/no valued attributes
    for complaint in complaintsRoot.iter('complaint'):
        resp = [resp for resp in complaint.iter('response')]
        assert 1 == len(resp)
        resp = resp[0]
        uniform_yes_no(resp)

    # sort complaints by complaint ID
    complaintsRoot[:] = sorted(complaintsRoot, key=lambda x: x.attrib['id'])

    # normalize indentation
    etree.indent(complaintsRoot)

    # step: single encoding: UTF8
    str = etree.tostring(complaintsRoot, encoding='utf8', pretty_print=True, xml_declaration=True)

    # return final xml outcome
    return str


def get_checksum(ss: bytearray) -> str:
    hash_object = hashlib.md5(ss)
    return hash_object.hexdigest()


def binary_compare(a: bytearray, b: bytearray) -> bool:
    if len(a) != len(b):
        return False
    idx = 0
    buf = 8
    while idx < len(a):
        ba = str(a[idx: buf])
        bb = str(b[idx: buf])
        if ba != bb:
            return False
        idx += buf
    return True


def print_lines(strA, ll_cnt):
    print('-------------------------------------------')
    #print(strA.decode('utf8'))
    arr = strA.decode('utf8').split('\n')[0:ll_cnt]
    print('\n'.join(arr))


fA_path = 'Consumer_Complaints_FileA.xml'
fB_path = 'Consumer_Complaints_FileB.xml'

print('Canonicalize', fA_path, '... ')
strA = canonicalize_utf8_encoded(fA_path)
print('Canonicalize', fB_path, '... ')
strB = canonicalize_utf8_encoded(fB_path)

#print_lines(strA, 20)
#print_lines(strB, 20)

#print_lines(strA, 10000)
#print_lines(strB, 10000)
print('-------------------------------------------')

print("checksum equal: ", get_checksum(strA) == get_checksum(strB))
is_same = binary_compare(strA, strB)
print("binary equal  : ", is_same)

assert is_same
# write final XML file
f = open("canonical.xml", "w")
f.write(strA.decode('utf8'))
f.close()

