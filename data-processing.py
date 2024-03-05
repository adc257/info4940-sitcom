import json
from datetime import datetime, timedelta
from pathlib import Path


# two different time formats in data, this cleans them into datetime objects
def string2datetime(string):
    try:
        return datetime.strptime(string.strip(), '%H:%M:%S:%f')

    except ValueError:
        try:
            return datetime.strptime(string.strip(), '%H:%M:%S,%f')

        except ValueError:
            return datetime.strptime(string.strip(), '%H:%M:%S')


def datetime2String(date):
    return datetime.strftime(date, '%H:%M:%S:%f')


# startTime and endTime must be in format String: "HH:MM:SS"
def getLinesBetween(startTime, endTime, lines_dict):
    return {
        lineStartTime: data
        for lineStartTime, data in lines_dict.items()
        if string2datetime(startTime) <= lineStartTime <= string2datetime(endTime)
    }


def getLinesAroundHumor(humorStartTime, threshold, lines_dict):
    startTime = humorStartTime - threshold
    endTime = humorStartTime + threshold
    return getLinesBetween(startTime.strftime('%H:%M:%S:%f'), endTime.strftime('%H:%M:%S:%f'), lines_dict)


def findHumor(file_path1):  # , file_path2
    humor_dict = {}
    # for file_path in [file_path1, file_path2]:
    # print(file_path.upper())
    with open(file_path1, 'r') as file:
        data = json.load(file)
        for dialog_num, info in data.items():
            if info['GT'] == 1:
                # print("humor")
                try:
                    humor_start, humor_end = string2datetime(info["Humor Start Time"]), string2datetime(
                        info["Humor End Time"])
                    duration = humor_end - humor_start
                    if timedelta(seconds=0) <= duration < timedelta(seconds=10):
                        humor_dict[humor_start] = humor_end
                except ValueError:
                    continue




    return dict(sorted(humor_dict.items(), key=lambda x: x[0]))


def reorganize_data(file):
    lines_dict = {}
    for dialog_num, info in file.items():
        dialog_turns = [key for key in info if key.startswith('Dialog Turn')]
        for turn in dialog_turns:
            try:
                start_time = string2datetime(info[turn]["Dialog Start time"])
            except ValueError:
                continue
            if start_time in lines_dict:
                continue
            else:
                lines_dict[start_time] = {
                    "EpisodeID": info['AV_ID'],
                    "Scene": info["Scene"],
                    "Recipients": info[turn]["Recipients"],
                    "Speaker": info[turn]["Speaker"],
                    "Dialogue": info[turn]["Dialog"],
                    "Dialogue Start Time": string2datetime(info[turn]["Dialog Start time"]),
                    "Dialogue End Time": string2datetime(info[turn]["Dialog End time"])
                }

    return dict(sorted(lines_dict.items(), key=lambda x: x[0]))


def tagHumorToLines(lines_dict, humor_dict):
    # TODO: set buffer
    buffer = timedelta(seconds=1)

    nHumorMissingLine = 0
    idxsHumorMissingLine = []

    humor_times = list(humor_dict.keys())
    dialog_times = list(lines_dict.keys())
    humorN = 0
    dialogN = 0
    while humorN < len(humor_dict):
        found_humor = False
        while dialogN < len(dialog_times) - 1 and not found_humor:
            laugh_start = humor_times[humorN]
            laugh_end = humor_dict[laugh_start]
            duration = laugh_end - laugh_start

            current_dialog_start = dialog_times[dialogN]
            current_dialog_end = lines_dict[current_dialog_start]['Dialogue End Time']
            next_dialog_start = dialog_times[dialogN + 1]

            if current_dialog_start <= laugh_start < next_dialog_start and laugh_start <= (current_dialog_end + buffer):
                lines_dict[current_dialog_start]['isHumor'] = True
                lines_dict[current_dialog_start]['humorDuration'] = duration
                found_humor = True
            dialogN += 1

        if not found_humor:
            dialogN = 0
            nHumorMissingLine += 1
            idxsHumorMissingLine.append(humorN)

        humorN += 1

    return lines_dict


directory = Path("data/DT_2/Raw")

for file_path in directory.rglob('*'):
    if file_path.is_file() and file_path.suffix == '.json':
        with open(file_path, 'r') as rFile:
            data = json.load(rFile)
            humor_dict = findHumor(file_path)
            lines_dict = reorganize_data(data)
            lines_dict_tagged = tagHumorToLines(lines_dict, humor_dict)

        new_file_path = "cleaned-" + str(file_path).replace("/DT_2/Raw", "")
        new_file_path = Path(new_file_path)

        if not new_file_path.exists():
            new_file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(new_file_path, 'w') as wFile:
            new_lines_dict = {}
            for key, value_dict in lines_dict_tagged.items():
                new_key = datetime2String(key)
                if "isHumor" in value_dict:
                    value_dict["humorDuration"] = str(value_dict["humorDuration"])

                value_dict.update({
                    "Dialogue Start Time": datetime2String(value_dict['Dialogue Start Time']),
                    "Dialogue End Time": datetime2String(value_dict['Dialogue End Time']),
                })
                new_lines_dict[new_key] = value_dict

            json.dump(new_lines_dict, wFile)