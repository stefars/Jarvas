from Agent.graph import Jarvas
from logging import basicConfig, INFO, DEBUG, WARNING

basicConfig(level=INFO, format='%(levelname)s: %(message)s')


#Also set up the workplace for everything else

def main():

    my_bot = Jarvas()

    while True:
        query = input(" > ")

        result = my_bot.call(query)
        print("-------")
        print(f"Jarvas: {result}")
        print("-------")



if __name__ == "__main__":
    main()