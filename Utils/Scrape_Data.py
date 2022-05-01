from wikipedia import search
import wikipediaapi

# import pandas as pd

def scrape_wikipedia(name_topic, verbose=True):
      
    final = {}
    api_wikipedia = wikipediaapi.Wikipedia(language='en', extract_format=wikipediaapi.ExtractFormat.WIKI)
    pages = []
  
    suggestions = search(name_topic)
    try:
        pages.append(api_wikipedia.page(suggestions[0]))
        final[suggestions[0]] = api_wikipedia.page(suggestions[0]).summary
        for title in suggestions: 
            if name_topic in title: 
                if api_wikipedia.page(title) not in pages:
                    pages.append(api_wikipedia.page(title))
                    try:
                        final[title] = api_wikipedia.page(title).content
                    except:
                        final[title] = api_wikipedia.page(title).summary
        return final
    except:
        print(f'Page not found for {name_topic} with suggested pages:  {suggestions}.')
    