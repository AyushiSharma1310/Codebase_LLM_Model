
def fetch_data_from_api(endpoint):
    # Simulate API call
    response = {'data': [1, 2, 3, 4]}
    return response['data']

def calculate_average(numbers):
    return sum(numbers) / len(numbers)

def main():
    data = fetch_data_from_api("https://api.example.com/data")
    avg = calculate_average(data)
    print(f"Average: {avg}")

if __name__ == "__main__":
    main()
