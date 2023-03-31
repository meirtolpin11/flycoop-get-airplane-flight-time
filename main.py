import requests
from datetime import datetime
import database

cookies = {
    'FS_LANG_CODE': 'EN',
    'FS_CUSTOMER_ID': 'flycoop',
    'COOKIES_ACCEPTED': 'true',
    'FS_CMS_STICKYNOTE_ALREADY_READ_flycoop_28': 'true',
}

headers = {
    'authority': 'flycoop-ato.evionica.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-AU,en-US;q=0.9,en-GB;q=0.8,en;q=0.7,he;q=0.6,ru;q=0.5',
    'cache-control': 'max-age=0',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://flycoop-ato.evionica.com',
    'referer': 'https://flycoop-ato.evionica.com/atom/pages/restricted/j_security_check',
    'sec-ch-ua': '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
}

calendar_url = r"https://flycoop-ato.evionica.com/atom/rest/calendar/" \
               "getBookingsForSchedulerTable?start={start}T00%3A00%3A00&end={end}T00%3A00%3A00&_=1680275906143"
airplanes_url = r"https://flycoop-ato.evionica.com/atom/rest/aircraft/getActiveAircraftsOfType?aircraftType=AIRPLANE"


def get_login_cookie(username, password):
    global cookies
    global headers

    data = {
        'j_username': f'flycoop:EN:{username}',
        'login': username,
        'j_password': password,
        'submitLogin': 'Login',
    }

    response = requests.post(
        'https://flycoop-ato.evionica.com/atom/pages/restricted/j_security_check',
        cookies=cookies,
        headers=headers,
        data=data,
    )

    return response.headers['set-cookie']


def get_all_flights(cookie):
    global cookies
    global headers
    global calendar_url

    cookies[cookie.split('=')[0]] = cookie.split('=')[1]

    resp = requests.get(calendar_url.format(start=datetime(2023, 2, 1).strftime('%Y-%m-%d'),
                                            end=datetime(2023, 4, 10).strftime('%Y-%m-%d')),
                        headers=headers, cookies=cookies)

    data = resp.json()
    return data


def get_airplanes_list(cookie):
    global airplanes_url
    global headers
    global cookies

    cookies[cookie.split('=')[0]] = cookie.split('=')[1]

    airplanes = requests.get(airplanes_url, headers=headers, cookies=cookies)

    return airplanes.json()


def parse_flights(flights):
    for flight in flights:
        if flight['eventType'] == "FLIGHT" and flight['status'] == 'FLOWN':
            departure = datetime.strptime(flight['start'], '%Y-%m-%d %H:%M')
            landing = datetime.strptime(flight['end'], '%Y-%m-%d %H:%M')
            database.Flights(airplane_id=int(flight["resourceId"]), departure=departure, landing=landing,
                             flight_time=(landing - departure). total_seconds() / 3600.0).save()
        elif flight['eventType'] == "AIRCRAFT_AVAILABILITY" and flight['remReasonCode'] == "AIRCRAFT_MAINTENANCE":
            end = datetime.strptime(flight['start'], '%Y-%m-%d %H:%M')
            database.Maintenance(airplane_id=int(flight['resourceId']), date=end).save()


def parse_airplanes(airplanes):
    for airplane in airplanes:
        database.Airplanes(airplane_id=airplane['id'], registration=airplane['regNumber'],
                           airplane_type=airplane['model']).save()


# noinspection SqlDialectInspection,SqlNoDataSourceInspection
def fetch_data_unsafe():
    cursor = database.sqlite_db.execute_sql('    \n'
                                            '        select \n'
                                            '            a.airplane_id,\n'
                                            '            a.registration,\n'
                                            '            a.airplane_type,\n'
                                            '            b.flight_time,\n'
                                            '            b.maintenance_date\n'
                                            '            \n'
                                            '        from airplanes as a\n'
                                            '        inner join (\n'
                                            '            select f.airplane_id as airplane_id, sum(f.flight_time) as flight_time, m.date as maintenance_date\n'
                                            '            from flights as f \n'
                                            '            inner join (\n'
                                            '                select airplane_id, max(date) as date from maintenance group by airplane_id\n'
                                            '            ) as m \n'
                                            '            on f.airplane_id == m.airplane_id\n'
                                            '            \n'
                                            '            where f.departure > m.date\n'
                                            '            GROUP by f.airplane_id\n'
                                            '        ) as b\n'
                                            '        on a.airplane_id == b.airplane_id\n'
                                            '        order by b.flight_time desc')
    for row in cursor.fetchall():
        print(row)


def main():
    username = input('username:')
    password = input('password:')
    auth_cookie = get_login_cookie(username, password)
    database.sqlite_db.drop_tables([database.Flights])
    database.sqlite_db.create_tables([database.Flights])
    parse_airplanes(get_airplanes_list(auth_cookie))
    parse_flights(get_all_flights(auth_cookie))
    fetch_data_unsafe()


if __name__ == '__main__':
    main()
