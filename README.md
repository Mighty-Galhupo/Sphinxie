# Sphinxie Discord Bot
A small program for a discord bot that asks a group questions where users can vote for each other.

Functions:
- Asks questions from the file "question_file.txt" and opens public threads for discussions and voting
- Set target channel to avoid direct questions there
- Command based activities
- Several debug commands for functionallity checks (Although some will not respond directly to the commands and instead just send a message due to the nature of the functions they check)
- Automatic daily questions (by default set to midnight, manageable via commands)
- Target channel, thread and time for automatic questions saved between runs of the bot
- Exclusion of questions that have already been asked

HOW TO USE:
1. Create a file named "token_file.txt" and paste in your discord application token
2. If you wish to use the automatic questions:
    - Add your questions to the file "question_file.txt", one per line
    - Use the command /set_channel in a channel to set that as the channel where questions will appear
    - Use the command /set_question_time hh mm to set the time at which questions are sent otherwise it will default to midnight in local time

Planned Features:
- A list of questions included with the program itself
- Poll summary at the end of every day (current rankings)
- Questions that target specific users/have options of types other than the users
- Preventing users from voting more than once
- Setting to hide who users voted for until final summary
- Restoring votes from previous session on boot
- Joining of saved data for target channels and times in one file