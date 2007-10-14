#!/usr/bin/ruby
# Some Comments about this file
# Hello World in ruby plus some other sillyness

puts 'Hello world'

def power(base, pow)
    return base ** pow
end

# Say Hello to somebody
def hello2(name)
    puts "Hello #{name}!"
end

# Greeter Class
class Greeter
    def intialize(name = "World")
        @name = name
    end
    def say_hello
        puts "Hello #{@name}!"
    end
    def say_bye
        puts "Bye #{@name}, come again."
    end
end

puts power(5, 2)
puts 5 ** 2

