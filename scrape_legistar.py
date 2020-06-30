import csv
import re

import bs4
import requests


def main(subdomain):
    scraper = LegistarSite(subdomain)
    results = scraper.scrape()
    write_csv(results, subdomain)

def write_csv(data, subdomain):
    headers = [
        'committee',
        'date',
        'time',
        'location',
        'details',
        'agenda_link',
        'minutes_links',
        'audio_video_link',
        'caption_notes',
    ]
    outfile = '/tmp/legistar_{}.csv'.format(subdomain)
    print("Writing {}".format(outfile))
    with open(outfile, 'w') as out:
        writer = csv.DictWriter(out, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

class LegistarSite:

    def __init__(self, subdomain):
        self.url = "https://{}.legistar.com/Calendar.aspx".format(subdomain)

    def scrape(self):
        session = requests.Session()
        # Initial request doesn't return past meetings, but we can
        # use the response to get session cookies that we can configure
        # for subsequent requests for older meeting data (typically by year).
        first_response  = session.get(self.url)
        cookies = first_response.cookies.get_dict()
        years = self._available_years(first_response.text)
        payload = []
        for year in years:
            cookie_header = self._prepare_cookie_header(cookies, year)
            response = self._request_page(session, cookie_header)
            data = self._extract_meeting_data(response.text)
            payload.extend(data)
        return payload

    def _available_years(self, page_text):
        #TODO: Scrape available years from the
        # dropdown menu in source code
        #soup = bs4.BeautifulSoup(page_text)
        return ['2018']

    def _prepare_cookie_header(self, cookies, year):
        """
        Prepares 'Cookie' header value for subsequent page requests.

        # NOTE: Below are cookies typically passed to site by browser

        ASP.NET_SessionId=iv1mmjvkbe4d14d4vkux3fzr;
        Setting-270-Calendar Options=info|;
        Setting-270-Calendar Year=2018;
        Setting-270-Calendar Body=All;
        Setting-270-ASP.calendar_aspx.gridUpcomingMeetings.SortExpression=MeetingStartDate DESC;
        Setting-270-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC;
        BIGipServerprod_insite_443=874644234.47873.0000'

        """
        cookies['Setting-270-Calendar Year'] = year
        return " ".join([
            "{}={};".format(k, v)
            for k, v in cookies.items()
        ])

    def _request_page(self, session, cookie_header):
        session.headers.update({
            'Cookie': cookie_header,
        })
        return session.get(self.url)

    def _extract_meeting_data(self, html):
        """Extract meetings under the All Meetings section.

        NOTE: Does not extract Upcoming Meetings.
        """
        soup = bs4.BeautifulSoup(html, 'html.parser')
        table = soup.find(
            'table',
            id='ctl00_ContentPlaceHolder1_gridCalendar_ctl00',
        )
        #TODO: Need to handle these paged results!
        result_page_links = []
        # Get data for additional, paged results,
        # excluding the current page
        for link in table.thead.table.find_all('a'):
            # current page has a class of 'rgCurrentPage',
            # but other pages (which we haven't yet scraped)
            # have no class set
            try:
                link.attrs['class']
            except KeyError:
                result_page_links.append(link)
        # Meeting info is stored in last tbody
        # inside parent table
        data_tbody = table.find_all('tbody')[-1]
        rows = data_tbody.find_all('tr')
        data = []
        for row in rows:
            row_data = self._get_meeting_data(row)
            data.append(row_data)
        return data

    def _get_meeting_data(self, row):
        cells = row.find_all('td')
        # TODO: Need to add handlers for most of these fields,
        # especially those that require generating a link to minutes, agenda
        # audio/video
        return {
            'committee': self._scrub(cells[0]),
            'date': self._scrub(cells[1]),
            'time': self._scrub(cells[3]),
            'location': self._scrub(cells[4]),
            'details': self._scrub(cells[5]),
            'agenda_link': self._scrub(cells[6]),
            'minutes_links': self._scrub(cells[7]),
            'audio_video_link': self._scrub(cells[8]),
            'caption_notes': self._scrub(cells[9]),
        }

    def _scrub(self, val):
        return re.sub(
            r'\n+',
            ' ',
            val.text.strip().replace('\xa0',' ')
        )


if __name__ == '__main__':
    subdomain = 'sunnyvaleca'
    main(subdomain)
