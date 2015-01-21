import os
import string
import re
import textwrap

class Convert(object):
    features_to_ignore = {'ncRNA': 1}
    feature_attributes_to_ignore = {'ID': 1, 'protein_id': 1}
    feature_attributes_translations = {'eC_number': 'EC_number'}
    feature_attributes_to_split_on_multiple_lines = {'inference': 1, 'EC_number': 1}
    feature_attributes_regex_to_change_feature_name = {'^16S ribosomal RNA': 'rRNA'}
    
    feature_attributes_inference_to_dbxref = {'similar to AA sequence:UniProtKB': 'UniProtKB/Swiss-Prot', 'protein motif:Pfam': 'PFAM', 'protein motif:CLUSTERS': "CDD", 'protein motif:Cdd': "CDD", 'protein motif:TIGRFAMs': "TIGRFAM"}
    
   
    def __init__(self, locus_tag = None, translation_table = 11):
        self.locus_tag = locus_tag
        self.translation_table = translation_table

    def blank_header(self):
      header = """\
ID   XXX; XXX; %s; genomic DNA; STD; %s; %d BP.
XX
AC   XXX;
XX
AC * _%s
XX
PR   Project:%s;
XX
DE   XXX;
XX
RN   [1]
RA   %s;
RT   "%s";
RL   %s.
XX
FH   Key             Location/Qualifiers
FH
"""
      return header
      
    def populated_header(self,
        num_bp=1,
        project="", 
        description="",
        contig_number=1, 
        authors="Pathogen Genomics", 
        title="Draft assembly annotated with Prokka",
        publication="Unpublished",
        genome_type="circular",
        classification="UNC",
        sequence_identifier=""
        ):

        header = self.blank_header()
        sequence_identifier_filtered  = re.sub(r'\W+', '', sequence_identifier)
        header_with_values = header % (genome_type, classification, num_bp,sequence_identifier_filtered, project,authors,title,publication)
        return header_with_values
        
    def source_template(self, sequence_length = None, organism = None, taxon_id = None, sequence_name = None):
        source_template = """\
FT   source          1..%d
FT                   /organism="%s"
FT                   /mol_type="genomic DNA"
FT                   /db_xref="taxon:%d"
FT                   /note="%s"
"""   % (sequence_length, organism,taxon_id,sequence_name)
        return source_template
        
    def construct_sequence(self,sequence):
      sequence_string = ''
      sequence_string += self.sequence_header(sequence)
      sequence_string += self.sequence_body(sequence)
      return sequence_string
    
    def sequence_header(self, sequence):
      sequence = sequence.lower()
      a = sequence.count('a')
      c = sequence.count('c')
      g = sequence.count('g')
      t = sequence.count('t')
      o = len(sequence) - a - c - g - t;
      return "SQ   Sequence %d BP; %d A; %d C; %d G; %d T; %d other;\n" % \
        (len(sequence), a, c, g, t, o)
      
    def sequence_body(self, sequence):
      sequence = sequence.lower()
      output = "     "
      i = 1
      for j in range(len(sequence)):
          output +=sequence[j]
          if (i) % 10 == 0:
              output += " "
          if (i) % 60 == 0 and i < len(sequence) :
              output += "%9s\n     " % (i)
          elif (i) % 60 == 0  and i == len(sequence):
             output += "%9s\n" % (i)
             return output
          i += 1

      if((i)%60 ==0):
        output += ' '*(66 -(((i-1)%60)/10) -((i-1)%60))  + "%9d\n" % (i - 1)
        return output
      else:
        output +=' '*(80-i%60-(i%60)/10-13) + "%9d\n" % (i - 1)
        return output
        
    def feature_header(self, feature_type = None, start = None, end = None, strand = None):
      string = ""
      cmp1 = ''
      cmp2 = ''
      if strand == '-':
          cmp1 = 'complement('
          cmp2 = ')'
      string += "FT   %s%s%s%d..%d%s\n" % (feature_type, ' ' * (16-len(feature_type)), cmp1, start, end, cmp2)
      return string
      
    def construct_feature(self, feature_type = None, start = None, end = None, strand = None, feature_attributes = {}):
      feature = ''
      if feature_type in self.features_to_ignore:
        return feature
        
      for feature_attribute_regex in self.feature_attributes_regex_to_change_feature_name.keys():
        for attribute_key in feature_attributes.keys():
          if re.search(feature_attribute_regex, feature_attributes[attribute_key]):
            feature_type = self.feature_attributes_regex_to_change_feature_name[feature_attribute_regex]
        
      feature += self.feature_header( feature_type ,start, end, strand )
      for attribute_key in feature_attributes.keys():
        feature += self.construct_feature_attribute( attribute_key = attribute_key, attribute_value = feature_attributes[attribute_key])
      
      if feature_type == 'CDS':
        feature += "FT                   /transl_table="+str(self.translation_table)+"\n"
      return feature
      
    def update_locus_tag(self,attribute_value):
      if self.locus_tag == None:
        return attribute_value
      locus_tag_parts = attribute_value.split('_')
      new_attribute = self.locus_tag + '_' +str(locus_tag_parts[-1])
      return new_attribute
      
    def search_hypo_protein(self, attribute_value):
      split_attribute_values = attribute_value.split( ',')
      
      for split_attribute_value in split_attribute_values:
        split_attribute_value_unknown = split_attribute_value.replace("nknown","ncharacterised")
        if split_attribute_value_unknown != 'hypothetical protein':
          return split_attribute_value_unknown
      
      return 'Uncharacterised protein'
    
    def construct_feature_attribute(self,attribute_key = None, attribute_value = None):
      feature_string = ''
      if attribute_key in self.feature_attributes_to_ignore:      
        return feature_string
      if attribute_key in self.feature_attributes_translations:
        attribute_key = self.feature_attributes_translations[attribute_key]
      
      if attribute_key == 'product':
          attribute_value = self.search_hypo_protein(attribute_value)
      
      if attribute_key == 'locus_tag':
        attribute_value = self.update_locus_tag(attribute_value)
      
      if attribute_key == 'EC_number':
          all_attribute_values = attribute_value.split( ',')
          split_attribute_values = list(set(all_attribute_values))
      else:
          split_attribute_values = attribute_value.split( ',')
      if attribute_key not in self.feature_attributes_to_split_on_multiple_lines:
        feature_string += self.create_multi_line_feature_attribute_string(attribute_key, split_attribute_values[0])
        
      else:
        for split_attribute_value in split_attribute_values:
          feature_string += self.create_multi_line_feature_attribute_string(attribute_key, split_attribute_value)
      return feature_string
      
    def update_inference_to_db_xref(self, attribute_key = None, attribute_value = None):
      if attribute_key == 'inference':
          for search_prefix in self.feature_attributes_inference_to_dbxref:
               if re.search(search_prefix, attribute_value):
                 return ('db_xref',attribute_value.replace(search_prefix, self.feature_attributes_inference_to_dbxref[search_prefix]))
      return (attribute_key,attribute_value)
      
    def create_multi_line_feature_attribute_string(self,attribute_key = None, attribute_value = None):
      if attribute_key == 'inference':
         (attribute_key, attribute_value) = self.update_inference_to_db_xref(attribute_key, attribute_value)
      
      wrapped_lines = textwrap.wrap("/%s=\"%s\"" % ( attribute_key, attribute_value) ,58)
      
      feature_string = ''
      for attribute_value_line in wrapped_lines:
        feature_string+= "FT%s" % (' ' * 19) + attribute_value_line + "\n"

      return feature_string    
      
      
