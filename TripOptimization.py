import googlemaps
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, time
import numpy as np
from scipy.interpolate import interp1d
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from adjustText import adjust_text

# Google Maps API key
gmaps = googlemaps.Client(key='***CLIENT KEY***')

# Gmail credentials
gmail_user = '***GMAIL ACCOUNT TO SEND TEXTS***'
gmail_password = '***GMAIL PASSWORD***'
recipient_phone_number = '***PHONE NUMBER***'
recipient_email = f'{recipient_phone_number}@msg.koodomobile.com' # REPLACE KOODO WITH PHONE PROVIDER MSG EMAIL

# Addresses
address_a = '***HOME ADDRESS***'
address_b = '4925 Dufferin St, North York, Ontario, Canada, M3H 5T6'

# Function to get trip duration
def get_trip_duration(gmaps, origin, destination, departure_time):
    directions = gmaps.directions(origin, destination, mode="driving", departure_time=departure_time, avoid=["tolls"])
    duration = directions[0]['legs'][0]['duration_in_traffic']['value'] / 60  # convert seconds to minutes
    return duration

# Create time series for plotting
def generate_times(start_hour, end_hour):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = datetime.combine(tomorrow.date(), time(start_hour, 0))
    end_time = datetime.combine(tomorrow.date(), time(end_hour, 0))
    times = [start_time + timedelta(hours=i) for i in range((end_time - start_time).seconds // 3600 + 1)]
    return times

times_a_to_b = generate_times(4, 14)  # 4 AM to 2 PM
times_b_to_a = generate_times(12, 22)  # 12 PM to 10 PM

# Get durations
durations_a_to_b = [get_trip_duration(gmaps, address_a, address_b, time) for time in times_a_to_b]
durations_b_to_a = [get_trip_duration(gmaps, address_b, address_a, time) for time in times_b_to_a]

# Generate half-hour intervals within the bounds
def generate_half_hour_intervals(start_hour, end_hour):
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = datetime.combine(tomorrow.date(), time(start_hour, 0))
    end_time = datetime.combine(tomorrow.date(), time(end_hour, 0))
    times = []
    current_time = start_time
    while current_time <= end_time:
        times.append(current_time)
        current_time += timedelta(minutes=30)
    return times

# Generate new time intervals within specified bounds
new_times_a_to_b = generate_half_hour_intervals(4, 14)
new_times_b_to_a = generate_half_hour_intervals(12, 22)

# Interpolation
time_nums_a_to_b = mdates.date2num(times_a_to_b)
time_nums_b_to_a = mdates.date2num(times_b_to_a)
new_time_nums_a_to_b = mdates.date2num(new_times_a_to_b)
new_time_nums_b_to_a = mdates.date2num(new_times_b_to_a)

# Ensure interpolation functions are bounded within the original data
interp_func_a_to_b = interp1d(time_nums_a_to_b, durations_a_to_b, kind='linear', bounds_error=False, fill_value="extrapolate")
interp_func_b_to_a = interp1d(time_nums_b_to_a, durations_b_to_a, kind='linear', bounds_error=False, fill_value="extrapolate")

# Interpolate within bounds
new_durations_a_to_b = interp_func_a_to_b(new_time_nums_a_to_b)
new_durations_b_to_a = interp_func_b_to_a(new_time_nums_b_to_a)

# Custom date formatter to remove leading zeros
def custom_date_formatter(x, pos=None):
    dt = mdates.num2date(x)
    hour = dt.hour % 12
    if hour == 0:
        hour = 12
    am_pm = 'am' if dt.hour < 12 else 'pm'
    return f'{hour} {am_pm}'

# Plotting
plt.figure(figsize=(6, 9), dpi=300)  # Taller figure size for vertical viewing
plt.plot(new_times_a_to_b, new_durations_a_to_b, marker='o', linestyle='-', linewidth=2.5)
plt.plot(new_times_b_to_a, new_durations_b_to_a, marker='o', linestyle='-', linewidth=2.5)

plt.xlabel('Departure Time', fontsize=16)
plt.ylabel('Trip Duration (minutes)', fontsize=16)
plt.title('Trip Duration vs. Departure Time', fontsize=18)
plt.grid(alpha=0.6)

plt.xticks(rotation=45, fontsize=14)
plt.yticks(fontsize=14)
plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(custom_date_formatter))  # Custom formatter
plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=2))

# Set x-axis limits
plt.xlim([datetime.now().replace(hour=4, minute=0, second=0, microsecond=0) + timedelta(days=1),
          datetime.now().replace(hour=22, minute=0, second=0, microsecond=0) + timedelta(days=1)])

# Add a tight layout to prevent clipping
plt.tight_layout()

# Annotate the last data points with labels
texts = [
    plt.text(new_times_a_to_b[-1], new_durations_a_to_b[-1], 'To UTIAS', fontsize=14, color='#1f77b4', ha='center', va='bottom'),
    plt.text(new_times_b_to_a[-1], new_durations_b_to_a[-1], 'To Home', fontsize=14, color='#ff7f0e', ha='center', va='bottom')
]
adjust_text(texts)

# Save plot to a file with high resolution
plot_filename = 'trip_duration_plot.jpg'
plt.savefig(plot_filename, format='jpg', dpi=500, bbox_inches='tight')  # Increased DPI and better bounding box

# Email the plot using Gmail
def send_email(gmail_user, gmail_password, recipient_email, plot_filename, date_taken):
    # Setup the MIME
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = recipient_email
    msg['Subject'] = 'Plot of Departure Time vs. Trip Duration'

    body = f'Here is your plot of departure time vs. trip duration for data taken on {date_taken}.'
    msg.attach(MIMEText(body, 'plain'))

    # Attach the plot
    with open(plot_filename, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={plot_filename}')
    msg.attach(part)

    # Login to Gmail and send the email
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)
    text = msg.as_string()
    server.sendmail(gmail_user, recipient_email, text)
    server.quit()

    print(f'Email sent to {recipient_email}')

# Date taken for the data
date_taken = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

# Send the email with the plot
send_email(gmail_user, gmail_password, recipient_email, plot_filename, date_taken)
