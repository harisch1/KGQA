import codecs
from bs4 import BeautifulSoup
# f = codecs.open("tester_url_data.html", 'r')
# htmldata = bytes(f.read(),'UTF-8')
# f.close()
# print(type(htmldata))

# f=codecs.open("tester_url_data.html", 'r', 'utf-8')
# document= BeautifulSoup(f.read())
# print(document)


def get_names(url = "http://www.artcyclopedia.com/artists/AZ.html"):
    # r = requests.get(url)
    f= codecs.open("tester_url_data.html", 'r', 'utf-8')
    soup = BeautifulSoup(f.read(), 'html5lib')
    # soup = BeautifulSoup(r.content, 'html5lib') 
    artists = []
    for tag in soup.find_all('strong'): 
        artists.append(tag.text)
    return list(filter(None, artists))[:-10]

artists = get_names()
print(len(artists))