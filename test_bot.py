import sys, traceback
sys.argv = ['bot', 'https://tavus.daily.co/ca83dc804ff4d479', 'ca83dc804ff4d479']
try:
    exec(open('conversation_bot.py').read().replace("if __name__ == \"__main__\":", "if True:"))
except Exception as e:
    traceback.print_exc()
