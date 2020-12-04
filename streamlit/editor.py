import streamlit as st
from streamlit_ace import st_ace
import pandas as pd
import numpy as np
import sdata

st.markdown("# sdata example")

@st.cache(persist=True, allow_output_mutation=True)
def get_sdata(name):
    return sdata.Data(name="data", uuid="38b26864e7794f5182d38459bab85842")


# print(help(st_ace))

# Spawn a new Ace editor
#st_ace(value='', placeholder='', height=500, language='plain_text', theme='chrome',
# keybinding='vscode', min_lines=None, max_lines=None, font_size=12,
# tab_size=4, wrap=False, show_gutter=True, show_print_margin=False,
# readonly=False, annotations=None, markers=None, auto_update=True, key=None)

sample_content_metadata = """name	data	str	-	
uuid	38b26864e7794f5182d38459bab85842	str	-	
"""
sample_content_comment="""# header
## subheader

a remarkable text



$f(x) = \\frac{1}{2}\\sin(x)$


[SCALE](https://www.scale.eu/de/unternehmen/ansprechpartner)

"""
sample_content_table = """name	value
1	1.2
2	2.3"""

@st.cache(persist=True, allow_output_mutation=True)
def get_content(component):
    print("get_content {}".format(component))
    if component=="metadata":
        return sample_content_metadata
    elif component == "table":
        return sample_content_table
    elif component == "comment":
        return sample_content_comment
    else:
        return None

data = get_sdata("data")

sdatapart = st.sidebar.radio(
    "choose sdata.Data component:",
    ('Metadata', 'Table', 'Comment'))
if sdatapart == 'Metadata':
    # ex = st.sidebar.button("create example data")
    # if ex:
    #     content_metadata = sample_content_metadata
    # else:
    #     content_metadata = ""

    st.markdown('## Metadata')
    content_metadata = get_content("metadata")
    content_metadata = content_metadata.replace("\t", ";")

    st.write("name; value; dtype; unit; description")
    content_metadata = st_ace(key="Meta", height=100, placeholder=sample_content_metadata, value=content_metadata,
                              language="rst")
    #st.write(content_metadata)
    cells = []
    for line in content_metadata.splitlines():
        cells.append(line.split(";"))
    try:
        df = pd.DataFrame(cells, columns=['name', 'value', 'dtype', 'unit', 'description'])
        st.write("parsed data")
        st.dataframe(df)
        data.metadata._attributes= {}
        for i, row in df.iterrows():
            print(row)
            print(row["name"], row.value, str(row.dtype), row.unit, row.description)
            data.metadata.add(row["name"], value=row["value"], dtype=str(row["dtype"]), unit=row["unit"], description=row["description"])

    except Exception as exp:
        st.markdown("### error: {}".format(exp))
        st.write(cells)
    st.write("sdata.Data.metadata")
    st.dataframe(data.metadata.df)

elif sdatapart == 'Table':
    st.markdown('## Table')
    content_table = get_content("table")
    content_table = content_table.replace("\t", ";")
    content_table = st_ace(key="table", height=100, placeholder=sample_content_table, value=content_table)
    content_table = content_table.replace("\t", ";")
    cells = []
    for line in content_table.splitlines():
        cells.append(line.split(";"))
    try:
        df = pd.DataFrame(cells[1:], columns=cells[0])
        st.write("parsed data")
        st.dataframe(df)
        data.df = df
    except:
        st.write(cells)

    st.write("sdata.Data.table")
    st.dataframe(data.table)


elif sdatapart == 'Comment':
    st.markdown('## Comment')
    content_comment = get_content("comment")
    content_comment = st_ace(key="comment", height=100, placeholder=content_comment,
                             language="markdown", value=content_comment)
    st.write(content_comment)
    data.comment = content_comment

else:
    st.write("You didn't select anything.")

st.sidebar.markdown("## sdata.Data Status")
st.sidebar.dataframe(data.describe())

st.markdown("## sdata.Data json")
content_json = st_ace(key="json", height=100, placeholder=sample_content_table, value=data.to_json(), readonly=True,
                      language="json", wrap=True)


#data2 = data.from_json(data.to_json())
st.markdown("## example python code")
content_python= r"""# python example
import sdata
json_str = r'''{}'''
data = sdata.Data.from_json(json_str)
print(data.describe())
print(data.metadata.df)
print(data.df)
print(data.comment)
""".format(data.to_json())
content_json = st_ace(key="python", height=100, placeholder=sample_content_table, value=content_python, readonly=True,
                      language="python", wrap=True)



# Display editor's content as you type

# cells = []
# for line in content.splitlines():
#     cells.append(line.split("\t"))
# df = pd.DataFrame(cells[1:], columns=cells[0])
#
# st.dataframe(df)
#
# st.write(content)
# # for lin in lines