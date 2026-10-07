from ddgs import DDGS

query = input("Search: ")

with DDGS() as ddgs:
    results = ddgs.text(query, max_results=10)

    for result in results:
        print("\nTitle:", result["title"])
        print("URL:", result["href"])
        print("Description:", result["body"])