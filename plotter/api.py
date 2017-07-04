import json
import io

from . import media

server_adress = '127.0.0.1:8000'

class ObjectRequestMixin(object):
    def execute_request(command, method='POST', data=None):
        import requests

        request_url = 'http://' + server_adress + '/plotter/{}/'

        url = self.request_url.format(command)

        if method == 'GET':
            r = requests.get(url, stream=True)
        elif method == 'POST':
            r = requests.post(url, data=data, stream=True)
        else:
            raise Exception('"{}" method not implemented'.format(method))
        
        if r.status_code != 200:
            raise Exception("HTTP Code: {}".format(r.status_code))

        buf = io.BytesIO()
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                buf.write(chunk)
        buf.seek(0)

        return buf

class FramePlotter(ObjectRequestMixin):

    # The following attributes are global image attributes.
    _frame_id = None         # bb_binary frame id.
    _title = None            # Text to plot in the upper left corner.
    _scale = 0.5             # Resizing of the image prior to plotting.
    _crop_coordinates = None # Allows displaying only a small part of the image.

    # The following attributes are vectors.
    _xs, _ys = None, None    # Positions of markers.
    _angles = None           # For arrows: rotation of markers.
    _sizes = None            # For circles: radius of circle.
    _colors = None           # matplotlib colors.
    _labels = None           # Text to print at each marker.

    def __init__(self, **args):
        for property in ("xs", "ys",
                         "angles", "sizes", "colors", "labels",
                         "frame_id", "title", "scale", "crop_coordinates"):
            if property not in args:
                continue
            setattr(self, "_" + property, args[property])
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    @classmethod
    def from_json(cls, data_json):
        data = json.loads(data_json)
        return cls.from_dict(data)
    def to_json(self):
        return json.dumps(dict(self))

    # Retrieve all properties as (name, value) pairs.
    # Used to convert to dictionary.
    def __iter__(self):
        def all_attributes():
            yield "frame_id", self._frame_id
            yield "xs", self._xs
            yield "ys", self._ys
            yield "angles", self._angles
            yield "sizes", self._sizes
            yield "colors", self._colors
            yield "labels", self._labels
            yield "title", self._title
            yield "scale", self._scale
            yield "crop_coordinates", self._crop_coordinates

        for (name, value) in all_attributes():
            if value is not None:
                yield (name, value)

    def get_image(self):
        """
            Requests the image from the backend server.
                
            Returns:
                numpy array containing the image
        """
        import matplotlib.pyplot as plt
        data = dict(frame_options=self.to_json())
        buf = self.execute_request("plot_frame", data=data)
        return plt.imread(buf)

class VideoPlotter(ObjectRequestMixin):

    # List of FramePlotter containing all required options.
    _frames = None
    # Auto-crop margin around the supplied coordinates.
    _crop_margin = None
    # Whether to automatically fill in missing frames.
    _fill_gaps = True

    # The following attributes can overwrite frame options.
    _crop_coordinates = None
    _scale = None

    def __init__(self, **args):
        for property in ("frames", "crop_margin",
                         "fill_gaps", "crop_coordinates", "scale"):
            if property not in args:
                continue
            setattr(self, "_" + property, args[property])

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
    @classmethod
    def from_json(cls, data_json):
        return cls.from_dict(json.loads(data_json))
    def to_json(self):
        return json.dumps(dict(self))

    # Retrieve all properties as (name, value) pairs.
    def __iter__(self):
        def all_attributes():
            yield "frames", self._frames
            yield "crop_margin", self._crop_margin
            yield "fill_gaps", self._fill_gaps
            yield "crop_coordinates", self._crop_coordinates
            yield "scale", self._scale

        for (name, value) in all_attributes():
            if value is not None:
                yield (name, value)

    def get_video(self, display_in_notebook=True, save_to_path=None, temppath='tmp/video_plot.mp4', display_scale=0.15):
        """
            Requests the video from the backend server.

            Args:
                display_in_notebook: whether to show the video in a notebook - must be saved to disk in order to do that
                save_to_path: path to save to video to
                temppath: required path to store the video for displaying it in a notebook
                display_scale: scaling of the notebook display

            Returns:
                io.BytesIO object containing the video data.
                This object might be closed if the video was saved to disk.
        """
        
        data = dict(video_options=self.to_json())
        buf = self.execute_request("plot_video", data=data)
        
        if save_to_path is not None:
            import shutil
            shutil.copyfileobj(buf, save_to_path)
            temppath = save_to_path
            
        if display_in_notebook:
            from IPython.display import HTML, display
            VIDEO_HTML = """
            <video style='margin: 0 auto;' width="{width}" height="{height}" controls>
                <source src="{src}" type="video/mp4">
            </video>
            """
            display(HTML(VIDEO_HTML.format(
                    src=temppath,
                    width=int(4000 * display_scale),
                    height=int(3000 * display_scale)
                )))

        return buf