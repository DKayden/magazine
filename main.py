from app import app, magazine

from threading import Thread

import asyncio


if __name__ == "__main__":
    
    magazine.robot.connect_all()

    magazine.server_modbus.datablock_input_register.setValues(address=0x02, values=1000)
    magazine.server_modbus.datablock_input_register.setValues(address=0x03, values=100)
    magazine.server_modbus.datablock_input_register.setValues(address=0x04, values=5)

    # Start the Flask server in a separate thread
    flask_thread = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000})
    flask_thread.daemon = True
    flask_thread.start()

    #Start the background tasks in separate threads
    status_thread = Thread(target=magazine.poll_status)
    status_thread.daemon = True
    status_thread.start()

    mission_thread = Thread(target=magazine.poll_mission)
    mission_thread.daemon = True
    mission_thread.start()

    # You cannot run asyncio.run() here as it blocks the main thread.
    # Instead, you should run your asyncio event loop in a separate thread.
    asyncio_thread = Thread(target=asyncio.run, args=(magazine.server_modbus.run_server_serial(),))
    asyncio_thread.start()

    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     print("Shutting down...")
    #     # Join non-daemon threads before exiting
    #     status_thread.join()
    #     mission_thread.join()

