"""Usage: jelly2groovy INPUTFILE OUTPUTFILE
          

Convert INPUTFILE from a Jenkins Jelly view to a Jenkins Groovy view and 
write to OUTPUTFILE.

Arguments:
  INPUTFILE        the path to the Jelly file to convert.
  OUTPUTFILE       the path to the Groovy file to write to.

"""

import re

from docopt import docopt

try:
  import xml.etree.cElementTree as ET
except ImportError:
  import xml.etree.ElementTree as ET

namespaceRE = re.compile(r'\{[^}]*\}')

def parse_and_get_ns(file):
  events = "start", "start-ns"
  root = None
  ns = {}
  for event, elem in ET.iterparse(file, events):
    if event == "start-ns":
      if elem[0] in ns and ns[elem[0]] != elem[1]:
        # NOTE: It is perfectly valid to have the same prefix refer
        #   to different URI namespaces in different parts of the
        #   document. This exception serves as a reminder that this
        #   solution is not robust.  Use at your own peril.
        raise KeyError("Duplicate prefix with different URI found.")
      ns[elem[0]] = '{%s}' % elem[1]
      ns['{%s}' % elem[1]] = elem[0]
    elif event == "start":
      if root is None:
        root = elem
  return ET.ElementTree(root), ns

def convert_value(input):
  res = input
  if input.startswith('${%'):
    res = '_("%s")' % input[3:-1]
  elif input.startswith('${') and input.endswith('}'):
    res = input[2:-1]
  else:
    res = '"%s"' % input.strip()
  return res

def generate_code(elem, out, ns, indent):
  m = namespaceRE.match(elem.tag)
  prefix = ''
  tag = elem.tag
  jellyCore = False
  output = True

  if m and m.group(0) == '{jelly:core}':
    jellyCore = True

  if m: # starts with a namespace, find out what namespace prefix it maps to
    prefix = '%s.' % ns[m.group(0)]
    tag = tag.replace(m.group(0), '')

  if not jellyCore:
    out.write('%s%s%s(' % ('  ' * indent, prefix, tag))

    attributes = []
    for attr in elem.attrib:
      attributes.append('%s: %s' % (attr, convert_value(elem.attrib[attr])))

    if elem.text and not elem.text.isspace():
      attributes.append(convert_value(elem.text))

    if len(attributes):
      out.write(', '.join(attributes))

    out.write(') ')
  else:
    if tag == 'if':
      out.write('%sif(%s)' % ('  ' * indent, convert_value(elem.attrib['test'])))
    elif tag == 'choose':
      output = False
    elif tag == 'invokeStatic':
      out.write('%sdef %s = %s.%s' % ('  ' * indent, elem.attrib['var'], elem.attrib['className'], elem.attrib['method']))
    elif tag == 'when':
      out.write('%sif(%s)' % ('  ' * indent, convert_value(elem.attrib['test'])))
    elif tag == 'otherwise':
      out.write('%selse' % ('  ' * indent,))
    
  if output:
    if len(elem):
      out.write('{')

    out.write('\n')

  for child in elem:
    generate_code(child, out, ns, indent + 1)
  
  if output and len(elem):
    out.write('%s}\n' % ('  ' * indent,))


if __name__ == '__main__':
  options = docopt(__doc__)
  
  inputfile = options['INPUTFILE']
  outputfile = options['OUTPUTFILE']

  tree, ns = parse_and_get_ns(inputfile)

  out = open(outputfile, "w")

  out.write('// Namespaces\n')
  for k in [key for key in ns.keys() if not key.startswith('{')]:
    out.write('%s = namespace("%s")\n' % (k, ns[k].replace('{', '').replace('}', '')))
  out.write('\n\n')

  root = tree.getroot()
  if root.tag.endswith('jelly'):
    root = root[0]

  generate_code(root, out, ns, 0)
  out.close()
  
