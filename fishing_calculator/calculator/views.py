from django.http import HttpResponse
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django import forms
import geocoder
g = geocoder.ip('me')
coordinateObject = g.latlng
customLoc = [0, 0]
class LocationForm(forms.Form):
        lat = forms.DecimalField(label="Latitude", initial=coordinateObject[0])
        lng = forms.DecimalField(label="Longitude", initial=coordinateObject[1])

# Create your views here.
def index(request):
    return render(request, "fishing_calculator/index.html", {
        "form": LocationForm()
    })


def calculate(request):
    if(request.method == "POST"):
        form = LocationForm(request.POST)
        
        if form.is_valid():
            customLoc = [request.POST.get("lat"), request.POST.get("lng")]
            #return HttpResponseRedirect(reverse("fishing_calculator/calculate"))
        else:
            return render(request, "fishing_calculator/index.html", {
                "form": form
            })
        
    def returnGraph():
        import requests as rq
        import json
        import pandas as pd
        import numpy as np
        import matplotlib.pyplot as plt
        import math
        import datetime
        from io import StringIO

        np.set_printoptions(formatter={'float_kind': lambda x: f'{x:.4f}'})
        # wind from the east, fish bite the least, wind from the north, dont go forth


        def to_farenheight(arr):
            return [i * (9/5) + 32 for i in arr]


        def aggregate(arr):  # aggregates 7 days of hourly readings into daily averages
            condensed = np.array([])
            if (len(arr) % 7 != 0):
                return 'Array not properly configured: len(arr) must be a multiple of 7'
            for i in range(0, (int)(len(arr)/24)):  # iterate days (0-6)
                sum = 0
                for j in range(0, 24):  # iterate hours (0 - 23)
                    sum += arr[i*24 + j]
                condensed = np.append(condensed, (sum/24))
            return condensed


        def grade_pressure(pressure_array):
            grades = np.array([0.000000] * len(pressure_array))
            for i in range(len(pressure_array)):
                quality: (float) = abs(pressure_array[i] - 30)
                # initial difference from ideal  max: 75pts
                weight: (float) = 25
                score: (float) = 2 / quality * 50
                if (score > 50):
                    score = 50
                score += weight
                if (i == len(pressure_array) - 1):
                    grades[i] = score + 12.5
                    continue
                deviation: (float) = pressure_array[i+1] - pressure_array[i]
                deviation_abs: (float) = abs(deviation)
                if (deviation < 0):  # if pressure drop incoming max: 10pts
                    temp: (float) = (deviation_abs / .04) * 10
                    if (temp > 10):
                        temp = 10
                    score += temp

                if (deviation_abs < .04):  # if pressure stable max: 15pts
                    temp: (float) = (.015 / deviation_abs) * 15
                    if (temp > 15):
                        temp = 15
                    score += temp

                grades[i] = '%.6f' % score
            return grades


        def grade_temp(temp_array):
            grades = np.array([0.000000] * len(temp_array))
            for i in range(len(temp_array)):
                quality: (float) = abs(temp_array[i] - 70)
                score: (float) = 0.00
                if (quality < 7):
                    score += (10 - (quality/7)*10)

                elif (quality < 20):
                    score += ((20 - quality) / 14) * 20 + 70

                elif (quality > 40):
                    score += 15
                else:
                    score += ((60 - quality) / 40) * 70
                grades[i] = '%.6f' % score
            return grades


        def grade_light(visibility_array):
            grades = np.array([0.000000] * len(visibility_array))
            weight = 50
            for i in range(len(visibility_array)):
                temp_difference = abs((100 - visibility_array[i]))
                score = temp_difference / 100 * 50 + 50

                grades[i] = '%.6f' % score
            return grades


        def aggregate_scores(pressure, temp, visibility):
            grades = np.array([0.000000] * len(pressure))
            weight = 50
            for i in range(len(pressure)):
                pressure_weight: (float) = pressure[i] / 100 * 45
                temp_weight: (float) = temp[i] / 100 * 45
                vis_weight: (float) = visibility[i] / 100 * 10
                total_weight: (float) = pressure_weight + temp_weight + vis_weight
                total_weight = total_weight / 100 * 50 + 50
                grades[i] = '%.6f' % total_weight
            return grades

        lat = customLoc[0]
        lng = customLoc[1]
        request = rq.get('https://api.open-meteo.com/v1/forecast?latitude=' + str(lat) + '&longitude=' + str(lng) + '&hourly=temperature_2m,surface_pressure,winddirection_10m,precipitation,visibility&temperature_unit=fahrenheit&timeformat=unixtime&timezone=America%2FChicago')


        byte_str = request._content
        dict = json.loads(byte_str.decode("utf-8").replace("'", '"'))

        dates = np.array(dict['hourly']['time'])
        temps = np.array(dict['hourly']['temperature_2m'])
        pressure = np.array(dict['hourly']['surface_pressure'])

        # pressure / 33.8639 = inHg
        for i in range(len(pressure)):
            pressure[i] /= 33.8638
        wind_direction = np.array(dict['hourly']['winddirection_10m'])
        precipitation = np.array(dict['hourly']['precipitation'])
        visibility = np.array(dict['hourly']['visibility'])
        # visibility / 1000 = km
        for i in range(len(visibility)):
            visibility[i] /= 1000
        dict_keys = list(dict.keys())
        # print(dict)

        df = pd.DataFrame({'temperature': temps, 'pressure': pressure, 'wind_direction': wind_direction,
                        'precipitation': precipitation, 'visibility': visibility})
        pressure_score = grade_pressure(pressure)

        score_df = pd.DataFrame({})
        score_df['pressure_score'] = pressure_score
        temp_score = grade_temp(temps)
        score_df['temp_score'] = temp_score
        light_score = grade_light(visibility)
        score_df['light_score'] = light_score
        score_df['total_score'] = aggregate_scores(
            pressure_score, temp_score, light_score)

        #(score_df['total_score'].min)
        # df = pd.DataFrame(dates, temps)
        fig = plt.figure()
        iterate = range(len(np.array(score_df['total_score'])))
        plt.plot(iterate, np.array(
            score_df['total_score']), marker='o', color="green")
        plt.ylabel("Score")
        plt.xlabel("Day")
        days = np.array([])
        j = 0
        day = np.array([])
        for i in iterate:
            if (i == 0):
                continue
            if (i % 24 == 0):
                day = np.append(day, i-12)
        day = np.append(day, day[len(day)-1]+24)
        print(day)
        print("customLoc", customLoc)
        # Get the current date
        today = datetime.date.today()

        # Create an array of dates for this week
        date_info = []
        
        for i in day:
            date_info.append(datetime.datetime.fromtimestamp(dates[int(i)]).strftime('%m/%d-%IPM'))
            plt.axvline(x=i, color='grey')

        plt.xticks(day, date_info, rotation=25)

        imgdata = StringIO()
        fig.savefig(imgdata, format='svg')
        imgdata.seek(0)

        data = imgdata.getvalue()
        return data

    context = returnGraph()
    return render(request, "fishing_calculator/calculate.html", {
        "latitude": customLoc[0],
        "longitude": customLoc[1],
        "graph": context
    })